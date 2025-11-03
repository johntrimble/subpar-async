from typing import Any, Generator, Literal, Tuple
import time
from socket import socket
from select import select

type Task = Generator[Any, Any, Any]
type Action = Literal["send", "throw"]

class Scheduler:
    ready: list[Task]
    sleeping: list[tuple[float, Task]]
    iowait_read: dict[socket, Task]
    iowait_write: dict[socket, Task]
    current: Task | None
    resume: dict[Task, Tuple[Action, Any]]

    def __init__(self):
        self.ready = []
        self.resume = {}
        self.iowait_read = {}
        self.iowait_write = {}

        # TODO: Make priority queue
        self.sleeping = []
        self.current = None

    def send_later(self, task: Task, value: Any = None, exc: BaseException | None = None) -> None:
        # Store the value for the task so that it can be retrieved when the task
        # runs
        if exc is not None:
            self.resume[task] = ("throw", exc)
        else:
            self.resume[task] = ("send", value)

        # Put the task back in the ready queue
        self.ready.append(task)

    def add_task(self, task: Task) -> None:
        self.ready.append(task)
    
    def _is_work_todo(self) -> bool:
        return any((self.ready, self.sleeping, self.iowait_read, self.iowait_write))

    def run(self):
        while self._is_work_todo():
            # If nothing is ready, check things we are waiting on (and 
            # potentially block/sleep)
            if not self.ready:
                # Figure out the amount of time for the next sleeping task to become
                # ready
                sleep_time = 0
                if self.sleeping:
                    expiration, _ = self.sleeping[0]
                    sleep_time = max(0, expiration - time.time())

                # Check if IO is ready for any tasks
                read_ready, write_ready, _ = select(
                    self.iowait_read.keys(), self.iowait_write.keys(), [], sleep_time
                )

                # Move ready IO tasks to the ready queue
                for sock in read_ready:
                    task = self.iowait_read.pop(sock)
                    self.ready.append(task)
                for sock in write_ready:
                    task = self.iowait_write.pop(sock)
                    self.ready.append(task)

                # Move any expired sleeping tasks to the ready queue
                current_time = time.time()
                while self.sleeping:
                    expiration, _ = self.sleeping[0]
                    if expiration < current_time:
                        _, task = self.sleeping.pop(0)
                        self.ready.append(task)
                    else:
                        break

            # TODO: I think this can only happen if nothing is sleeping, nothing
            # is ready, and we only have stuff waiting on IO. I don't think we
            # can actually get out of this state until something happens
            # IO-wise. Maybe we should use a timeout larger than zero above with
            # the select call?
            if not self.ready:
                continue

            # Get the next ready task and run it
            # print("ready", self.ready)
            self.current = self.ready.pop(0)
            try:
                action, value = self.resume.pop(self.current, ("send", None))

                # Switch on the action value
                match action:
                    case "send":
                        self.current.send(value)
                    case "throw":
                        self.current.throw(value)
                    case _:
                        raise RuntimeError(f"Unsupported resume action: {action}")

                if self.current:
                    self.ready.append(self.current)
            except StopIteration:
                pass
            self.current = None
    
    def sleep(self, delay: float | int) -> Generator[None, None, None]:
        assert self.current, "Expected task to be running"
        expiration = time.time() + delay
        self.sleeping.append((expiration, self.current))
        self.sleeping.sort(key=lambda x: x[0])
        self.current = None
        yield
    
    def sock_accept(self, sock: socket) -> Generator[None, None, tuple[socket, Any]]:
        # TODO: Can there be multiple IO operations against the same socket?
        # Maybe this needs to be a list of tasks? Or maybe the mapping should be
        # task to socket?
        self.iowait_read[sock] = self.current
        self.current = None
        yield # wait for a connection
        return sock.accept()

    def sock_recv(self, sock: socket, maxbytes) ->Generator[None, None, bytes]:
        self.iowait_read[sock] = self.current
        self.current = None
        yield # wait for there to be something to read
        return sock.recv(maxbytes)

    def sock_send(self, sock: socket, data: bytes) -> Generator[None, None, int]:
        self.iowait_write[sock] = self.current
        self.current = None
        yield # wait until ready to send
        # TODO: Is bytes a ReadableBuffer? Hope so.
        return sock.send(data)


sched = Scheduler()


class QueueClosed(Exception):
    pass


class AsyncQueue:
    items: list[Any]
    waiting: list[Task]
    _closed: bool

    def __init__(self):
        self.items = []
        self.waiting = []
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    def close(self):
        self._closed = True
        if not self.items:
            for task in self.waiting:
                sched.send_later(task, exc=QueueClosed())

    def get(self):
        if self.closed:
            raise QueueClosed()

        # We have a value, return it
        # TODO: Should we actually return here or should we call send_later
        # with the value? If we do it that way, who would pull us off the
        # waiting list? Maybe we send_later and skip the waiting list?
        if self.items:
            return self.items.pop(0)

        # We have no value, park the generator until we are sent a value
        self.waiting.append(sched.current)
        sched.current = None
        item = yield
        return item

    # TODO: Make `put` a generator. I think this is needed to support a bouneded
    # queue as we will have to park if put is called when the queue is full.
    def put(self, item):
        if self.closed:
            raise QueueClosed()

        if self.waiting:
            # We have a task waiting to receive a value
            task = self.waiting.pop(0)
            sched.send_later(task, item)
        else:
            # No one is waiting, just append the item
            self.items.append(item)
    
    def empty(self) -> bool:
        return len(self.items) == 0


class AsyncSemaphore:
    def __init__(self, value=1):
        # Since we already have AsyncQueue working, we'll just base this
        # implementations on that
        self._queue = AsyncQueue()

        # Put as many tokens on the queue as indicated by value
        for _ in range(value):
            self._queue.put(None)
    
    def acquire(self):
        # Pop a token from the queue. If there are no tokens, we will get
        # parked.
        yield from self._queue.get()
    
    def release(self):
        # Put a token back on the queue
        self._queue.put(None)

    def locked(self) -> bool:
        # If the queue is empty, then we have no tokens left, so we are locked
        return self._queue.empty()


class AsyncLock:
    def __init__(self):
        self._semaphore = AsyncSemaphore(value=1)
    
    def acquire(self):
        yield from self._semaphore.acquire()
    
    def release(self):
        # For Locks, it is an error to release when we are not locked
        if not self._semaphore.locked():
            raise RuntimeError("Lock.release() called when not locked!")
        self._semaphore.release()
