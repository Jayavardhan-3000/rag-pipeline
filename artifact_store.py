import json
from pathlib import Path

from chunk_type import MermaidDiagram, Section

class ArtifactStore:
    @staticmethod
    def save(sections: list[Section], path: str | Path):
        data = {}
        for section in sections:
            if not section.mermaid_diagrams:
                continue
            data[section.section_id] = [
                {
                    "previous": diagram.previous,
                    "previous_embedding": diagram.previous_embedding,
                    "content": diagram.content,
                    "following": diagram.following,
                    "following_embedding": diagram.following_embedding
                }
                for diagram in section.mermaid_diagrams
            ]
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
    @staticmethod
    def load(path: str | Path) -> dict[str, list[MermaidDiagram]]:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        artifacts = {}
        for section_id, diagrams in data.items():
            artifacts[section_id] = [
                MermaidDiagram(
                    previous=diagram["previous"],
                    previous_embedding=diagram["previous_embedding"],
                    content=diagram["content"],
                    following=diagram["following"],
                    following_embedding=diagram["following_embedding"]
                )
                for diagram in diagrams
            ]

        return artifacts