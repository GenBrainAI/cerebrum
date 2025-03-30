import asyncio
from functools import wraps

async def run_async(coro):
    """Safely run an async coroutine in Streamlit.
    
    This function handles the execution of async coroutines in Streamlit
    without trying to create a new event loop if one already exists.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're already in a running event loop, just await the coroutine
            return await coro
        else:
            # If no loop is running, we can run the coroutine to completion
            return await coro
    except RuntimeError:
        # If there's no event loop in this thread, create one and run
        return asyncio.run(coro)

def run_async_sync(coro):
    """Synchronously run an async coroutine, handling all event loop complexities.
    
    This is a simpler wrapper for Streamlit components that need to run async 
    functions without dealing with async/await syntax.
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine execution
    """
    try:
        # First try to get the current event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in thread, create one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                
        # Check if the loop is running
        if loop.is_running():
            # We need to use a different approach when the loop is running
            # Create a new thread with its own event loop
            import threading
            import concurrent.futures
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()
            
            # Run in a separate thread
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        else:
            # If the loop exists but isn't running, we can just use it
            return loop.run_until_complete(coro)
            
    except Exception as e:
        import traceback
        print(f"Error in run_async_sync: {str(e)}")
        print(traceback.format_exc())
        raise

def streamlit_async(func):
    """Decorator to handle async functions in Streamlit.
    
    This decorator wraps an async function to make it usable in Streamlit
    by handling the event loop management.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task in the existing loop
                async def run():
                    return await func(*args, **kwargs)
                return run()
            else:
                # No running loop, execute directly
                return asyncio.run(func(*args, **kwargs))
        except Exception as e:
            import traceback
            print(f"Error in streamlit_async: {str(e)}")
            print(traceback.format_exc())
            raise
            
    return wrapper 