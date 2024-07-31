from typing import Iterator
from abc import ABC, abstractmethod
from falkordb_gemini_kg.classes.Document import Document
from falkordb_gemini_kg.document_loaders import (
    PDFLoader,
    TextLoader,
    URLLoader,
    HTMLLoader,
    CSVLoader,
    JSONLLoader,
)


def Source(path: str, instruction: str | None = None) -> "AbstractSource":
    """
    Creates a source object

    Parameters:
        path (str): path to source
        instruction (str): source specific instruction for the LLM

    Returns:
        AbstractSource: source
    """

    if not isinstance(path, str) or path == "":
        raise Exception("Invalid argument, path should be a none empty string.")

    s = None

    if ".pdf" in path.lower():
        s = PDF(path)
    elif ".html" in path.lower():
        s = HTML(path)
    elif "http" in path.lower():
        s = URL(path)
    elif ".csv" in path.lower():
        s = CSV(path)
    elif ".jsonl" in path.lower():
        s = JSONL(path)
    else:
        s = TEXT(path)

    # Set source instructions
    s.instruction = instruction

    return s


class AbstractSource(ABC):
    """
    Abstract class representing a source file
    """

    def __init__(self, path: str):
        self.path = path
        self.loader = None
        self.instruction = ""

    def load(self) -> Iterator[Document]:
        return self.loader.load()

    def __eq__(self, other) -> bool:
        if not isinstance(other, AbstractSource):
            return False

        return self.path == other.path

    def __hash__(self):
        return hash(self.path)


class PDF(AbstractSource):
    """
    PDF resource
    """

    def __init__(self, path):
        super().__init__(path)
        self.loader = PDFLoader(self.path)


class TEXT(AbstractSource):
    """
    TEXT resource
    """

    def __init__(self, path):
        super().__init__(path)
        self.loader = TextLoader(self.path)


class URL(AbstractSource):
    """
    URL resource
    """

    def __init__(self, path):
        super().__init__(path)
        self.loader = URLLoader(self.path)


class HTML(AbstractSource):
    """
    HTML resource
    """

    def __init__(self, path):
        super().__init__(path)
        self.loader = HTMLLoader(self.path)


class CSV(AbstractSource):
    """
    CSV resource
    """

    def __init__(self, path, rows_per_document: int = 50):
        super().__init__(path)
        self.loader = CSVLoader(self.path, rows_per_document)


class JSONL(AbstractSource):
    """
    JSONL resource
    """

    def __init__(self, path, rows_per_document: int = 50):
        super().__init__(path)
        self.loader = JSONLLoader(self.path, rows_per_document)
