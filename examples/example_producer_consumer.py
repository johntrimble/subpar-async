from subpar_async.scheduler import QueueClosed, sched, AsyncQueue

def producer(q: AsyncQueue):
    for i in range(10):
        print(f"Producing {i}")
        q.put(i)
        yield from sched.sleep(3)
    q.close()

def consumer(q: AsyncQueue):
    while True:
        try:
            item = yield from q.get()
            print(f"Consumed {item}")
        except QueueClosed:
            print("Queue closed, consumer exiting")
            break

q = AsyncQueue()
sched.add_task(producer(q))
sched.add_task(consumer(q))
sched.run()
