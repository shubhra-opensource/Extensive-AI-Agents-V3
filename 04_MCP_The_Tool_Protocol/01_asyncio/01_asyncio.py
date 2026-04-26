# ++++++++++++++++++++++++++++++++Without Asyncio+++++++++++++++++++++++++++++++ 
# import time

# def task1():
#     time.sleep(2)
#     print("Task 1 done")

# def task2():
#     time.sleep(2)
#     print("Task 2 done")

# task1()
# task2()

# +++++++++++++++++++++++++++++++++++++++++++++++Faulty Asyncio +++++++++++++++++++++++++++++++++++++++++++++++ 

# import asyncio

# async def task1():
#     await asyncio.sleep(6)
#     print("Task 1 done")

# async def task2():
#     await asyncio.sleep(6)
#     print("Task 2 done")

# asyncio.run(task1())
# asyncio.run(task2())

# +++++++++++++++++++++++++++++++++++++++++++++++Correct Asyncio +++++++++++++++++++++++++++++++++++++++++++++++ 

import asyncio

async def task1():
    await asyncio.sleep(2)
    print("Task 1 done")

async def task2():
    await asyncio.sleep(2)
    print("Task 2 done")

async def main():
    await asyncio.gather(task1(), task2())

asyncio.run(main())

