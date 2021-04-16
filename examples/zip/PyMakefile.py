from pymake.targets.target import FilePath
from pymake import *


@makes('files.zip', 'files/*')
async def zip(out: FilePath, files: Dependencies):
    await sh(f"zip -r {out} {files}")

if __name__ == "__main__":
    cli(__file__, loglevel='DEBUG')
