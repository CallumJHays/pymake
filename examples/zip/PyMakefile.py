from pymake import *

@makes('files.zip', 'files/*')
async def zip():
    with open('files.zip', 'w') as f:
        f.write('lets pretend this works')

if __name__ == "__main__":
    cli(__file__)
