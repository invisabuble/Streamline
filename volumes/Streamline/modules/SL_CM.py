import asyncio

class SL_CM :
    # Streamline Context Manager for async streamline tasks.

    def __init__ (self, interval) :
        # Initialise the context manager.
        self.interval = interval           # Defines how long the task sleeps between running tasks.
        self._task = None                  # Asyncio task handle. 
        self._stop_event = asyncio.Event() # Asyncio stop flag to cancel task.

    async def __aenter__ (self) :
        # Async entrypoint for the context manager.
        self.log("Starting up...")
        self._task = asyncio.create_task(self._run()) # Create the task using the _run() method.
        return self                                   # Return the created instance of this object.
    
    async def __aexit__ (self, exc_type, exc, tb) :
        # Async exit point for the context manager.
        self.log("Shutting down...")
        self._stop_event.set()   # Set the stop event to signal the task to end.

        if (self._task) :

            self._task.cancel()  # Cancel the running task.

            try:
                await self._task # Wait until the running task has finished.

            except asyncio.CancelledError:
                pass
            
        await self.Cleanup()
        self.log("Shutdown and Cleaned up.")

    def log (self, message) :
        # Log a message from an object.
        print(f"[{self.__class__.__name__}] - {message}")

    async def _run (self) :
        # Internal method run by the task.
        try:

            while not self._stop_event.is_set() :  # Continue running the task whilst the stop flag isnt set.

                await self.SL_Task()               # Await the SL_Task (Overwritten for each derivation of this base class)
                await asyncio.sleep(self.interval) # Sleep for the interval

        except Exception as e:

            self.log(f"Hit exception : {e}")
            raise

    async def SL_Task (self) :
        # Async task overwritten for each derived class.
        pass

    async def Cleanup (self) :
        # Async cleanup taks overwritten for each derived class.
        pass