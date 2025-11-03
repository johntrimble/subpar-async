from subpar_async.scheduler import sched, AsyncSemaphore

def named_task(name: str, semaphore: AsyncSemaphore):
    yield from semaphore.acquire()
    try:
        print(f"{name} acquired semaphore")
        yield from sched.sleep(4)
    finally:
        semaphore.release()

semaphore = AsyncSemaphore(value=2)

for i in range(20):
    sched.add_task(named_task(f"task-{i}", semaphore))

# Should see tasks run in groups of 2
sched.run()
