
import unittest
from langchain_tools import BaseTool
from your_module import ExampleLangchainTool

class TestExampleLangchainTool(unittest.TestCase):

    def setUp(self):
        self.tool = ExampleLangchainTool(name="test_tool")

    def test_initialization(self):
        self.assertEqual(self.tool.name, "test_tool")

    def test_execute_success(self):
        task = "SampleTask"
        result = self.tool.execute(task)
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['result'], f"Processed {task}")

    def test_execute_error(self):
        with unittest.mock.patch.object(self.tool, '_process_task', side_effect=Exception('Test error')):
            result = self.tool.execute("SampleTask")
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['message'], 'Test error')

    def test_process_task(self):
        task = "SampleTask"
        result = self.tool._process_task(task)
        self.assertEqual(result, f"Processed {task}")

if __name__ == '__main__':
    unittest.main()
