import asyncio
import unittest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import logging

# Attempt to import the class to be tested
try:
    from src.server.tools.human_tools import HumanInputTool
except ImportError:
    # Fallback for different project structures or if running test directly
    # This assumes a certain project structure relative to the test file.
    # Adjust as necessary if your structure is different.
    sys.path.append('../../') # Adjust based on actual file location
    from src.server.tools.human_tools import HumanInputTool


# Configure logging to capture log messages for assertions if needed
# For simplicity in these tests, we'll mostly check behavior and state,
# but a more advanced setup could use a log handler.
logging.basicConfig(level=logging.DEBUG)


class TestHumanInputTool(unittest.IsolatedAsyncioTestCase):

    def patch_streamlit(self):
        # Helper to consistently patch Streamlit presence
        mock_st = MagicMock()
        mock_st.session_state = MagicMock(spec=dict) # Mock session_state as a dict-like object

        # Apply patches for 'streamlit' module and 'streamlit.session_state'
        # Patch 'src.server.tools.human_tools.st' if HumanInputTool imports st directly
        self.st_patch = patch('src.server.tools.human_tools.st', mock_st)
        self.sys_modules_patch = patch.dict(sys.modules, {'streamlit': mock_st})
        
        self.mock_st_module = self.sys_modules_patch.start()
        self.mock_st_object = self.st_patch.start()
        return self.mock_st_object.session_state

    def unpatch_streamlit(self):
        if hasattr(self, 'st_patch'):
            self.st_patch.stop()
        if hasattr(self, 'sys_modules_patch'):
            self.sys_modules_patch.stop()


    async def asyncSetUp(self):
        self.tool = HumanInputTool()
        # Clean up any shared state from previous tests
        self.tool._pending_futures.clear()
        # Mock st.session_state for each test, injected where needed
        self.mock_session_state = {} 

        # It's important that HumanInputTool uses the same logger object
        # if we want to patch or inspect its logger. For now, we assume it creates its own.


    async def asyncTearDown(self):
        # Ensure all futures are cancelled or awaited to prevent warnings
        for future in self.tool._pending_futures.values():
            if not future.done():
                future.cancel()
                try:
                    await future
                except asyncio.CancelledError:
                    pass
        self.tool._pending_futures.clear()
        self.unpatch_streamlit()


    async def test_streamlit_run_and_submit_interaction(self):
        """Test the async interaction between streamlit_run and submit_response."""
        mock_session_state = self.patch_streamlit()
        
        question = "Test question?"
        session_id_dummy = "test_session_1" # Not directly used by current future logic but passed
        expected_answer = "Test answer"

        # Create a task for streamlit_run
        run_task = asyncio.create_task(self.tool.streamlit_run(question, session_id_dummy))

        # Allow streamlit_run to proceed until it awaits the future
        await asyncio.sleep(0.01) 

        # Find the request_id (there should be only one future)
        self.assertEqual(len(self.tool._pending_futures), 1)
        request_id = list(self.tool._pending_futures.keys())[0]
        
        # Verify st.session_state population
        self.assertEqual(mock_session_state[f"human_input_question_{request_id}"], question)
        self.assertTrue(mock_session_state[f"human_input_waiting_{request_id}"])
        self.assertEqual(mock_session_state["human_input_active_request_id"], request_id)

        # Simulate Streamlit callback calling submit_response
        self.tool.submit_response(request_id, expected_answer)

        # Await the result of streamlit_run
        actual_answer = await run_task
        
        self.assertEqual(actual_answer, expected_answer)
        
        # Verify cleanup
        self.assertEqual(len(self.tool._pending_futures), 0)
        self.assertNotIn(f"human_input_question_{request_id}", mock_session_state)
        self.assertNotIn(f"human_input_waiting_{request_id}", mock_session_state)
        self.assertNotIn("human_input_active_request_id", mock_session_state) # Cleared if it was this one

    @patch('src.server.tools.human_tools.HumanInputTool.console_run', return_value="Console response")
    async def test_run_dispatches_to_console(self, mock_console_run):
        """Test _run dispatches to console_run when Streamlit is not detected."""
        # Ensure Streamlit is not in sys.modules for this test
        if 'streamlit' in sys.modules:
            del sys.modules['streamlit'] # Crude, but effective for testing this path
        # Also ensure the 'st' object within human_tools is None or not a MagicMock that implies Streamlit
        with patch('src.server.tools.human_tools.st', None):
             question = "Test question for console?"
             await self.tool._run(question)
             mock_console_run.assert_called_once_with(question, **{})


    @patch('src.server.tools.human_tools.HumanInputTool.streamlit_run', new_callable=AsyncMock)
    async def test_run_dispatches_to_streamlit(self, mock_streamlit_run):
        """Test _run dispatches to streamlit_run when Streamlit is detected."""
        self.patch_streamlit() # Patches sys.modules and the 'st' object in human_tools
        mock_streamlit_run.return_value = "Streamlit response"
        
        question = "Test question for streamlit?"
        session_id_arg = "session123"
        await self.tool._run(question, session_id=session_id_arg) # Pass kwargs
        
        mock_streamlit_run.assert_called_once()
        # Check that question and any kwargs are passed through
        called_args, called_kwargs = mock_streamlit_run.call_args
        self.assertEqual(called_args[0], question)
        self.assertEqual(called_kwargs.get('session_id'), session_id_arg)


    async def test_streamlit_run_future_gets_exception(self):
        """Test streamlit_run when the future it awaits gets an exception."""
        mock_session_state = self.patch_streamlit()
        question = "Question for future exception"
        
        run_task = asyncio.create_task(self.tool.streamlit_run(question))
        await asyncio.sleep(0.01) # Let streamlit_run set up the future

        self.assertEqual(len(self.tool._pending_futures), 1)
        request_id = list(self.tool._pending_futures.keys())[0]
        future_to_except = self.tool._pending_futures[request_id]

        # Simulate an error source causing the future to have an exception
        test_exception = ValueError("Future failed")
        future_to_except.set_exception(test_exception)

        response = await run_task
        self.assertIn("ERROR: Human input failed due to: Future failed", response)
        
        # Check cleanup
        self.assertNotIn(request_id, self.tool._pending_futures)
        self.assertNotIn(f"human_input_question_{request_id}", mock_session_state)
        self.assertNotIn(f"human_input_waiting_{request_id}", mock_session_state)


    @patch('src.server.tools.human_tools.uuid.uuid4', side_effect=RuntimeError("UUID generation failed"))
    async def test_streamlit_run_internal_error_early(self, mock_uuid_error):
        """Test streamlit_run when an error occurs early (e.g., uuid fails)."""
        self.patch_streamlit()
        question = "Test question for early fail"
        
        # Expecting the error message from the tool's own try-except
        response = await self.tool.streamlit_run(question)
        
        self.assertIn("ERROR: Human input failed due to: UUID generation failed", response)
        self.assertEqual(len(self.tool._pending_futures), 0) # No future should have been added


    @patch.object(logging, 'warning') # Patch the logger directly
    async def test_submit_response_invalid_request_id(self, mock_log_warning):
        """Test submit_response with an invalid request_id."""
        self.patch_streamlit() # To allow session_state interaction if any
        initial_futures_count = len(self.tool._pending_futures)
        
        self.tool.submit_response("invalid_id", "test answer")
        
        mock_log_warning.assert_called_with("No pending future found for ID invalid_id when submitting response. It might have timed out or errored.")
        self.assertEqual(len(self.tool._pending_futures), initial_futures_count)


    @patch.object(logging, 'error') # Patch the logger
    async def test_submit_response_future_set_result_exception(self, mock_log_error):
        """Test submit_response when future.set_result() raises an exception."""
        mock_session_state = self.patch_streamlit()
        question = "Test for set_result exception"
        
        # Start streamlit_run to create a pending future
        # We don't await it here, just let it set up
        asyncio.create_task(self.tool.streamlit_run(question))
        await asyncio.sleep(0.01)

        self.assertEqual(len(self.tool._pending_futures), 1)
        request_id = list(self.tool._pending_futures.keys())[0]
        future_to_break = self.tool._pending_futures[request_id]

        # Mock future_to_break.set_result to raise an error
        future_to_break.set_result = MagicMock(side_effect=RuntimeError("Failed to set result"))

        self.tool.submit_response(request_id, "test answer")
        
        # Check that an error was logged
        self.assertTrue(mock_log_error.called)
        args, _ = mock_log_error.call_args
        self.assertIn(f"Error in HumanInputTool.submit_response (request_id: {request_id}): Failed to set result", args[0])

        # The future should have been removed from _pending_futures by submit_response's error handling
        self.assertNotIn(request_id, self.tool._pending_futures)
        # Session state should also be cleaned up
        self.assertNotIn(f"human_input_question_{request_id}", mock_session_state)
        self.assertNotIn(f"human_input_waiting_{request_id}", mock_session_state)


if __name__ == '__main__':
    unittest.main()
