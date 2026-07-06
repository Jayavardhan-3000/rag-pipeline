import os
import asyncio
from pathlib import Path

from llama_cloud import AsyncLlamaCloud
from dotenv import load_dotenv
from parsed_page import ParsedPage

load_dotenv()

    
class MarkdownParser:
    """
    This Class connects to the LlamaIndex Parser and parses down all the documents from the directory
    and turn them into rich meaningful markdown.
    
    """
    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.client = AsyncLlamaCloud(
            api_key=os.getenv("LLAMA_CLOUD_API_KEY")
        )
        self.semaphore = asyncio.Semaphore(5)

    async def parse_file(self, path: Path) -> list[ParsedPage]:
        async with self.semaphore:
            file_obj = await self.client.files.create(
                file=path,
                purpose="parse"
            )
            result = await self.client.parsing.parse(
                version="latest",
                file_id=file_obj.id,
                tier="agentic",
                expand=["markdown"],
            )
        return [
                ParsedPage(
                page_number=page.page_number,
                markdown=page.markdown
    )
    for page in result.markdown.pages
]

    async def parse_directory(self) -> dict[str, list[ParsedPage]]:
        paths = list(self.directory.glob("*.pdf"))
        tasks = [
            self.parse_file(path)
            for path in paths
        ]
        markdowns = await asyncio.gather(*tasks)
        return {
            path.stem: markdown
            for path, markdown in zip(paths, markdowns)
        }
