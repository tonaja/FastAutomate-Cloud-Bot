from langchain.document_loaders.pdf import PyPDFDirectoryLoader


def load_documents():
    document_loader = PyPDFDirectoryLoader('C:\\Users\\FaceGraph\\Downloads\\langgraph\\data')
    return document_loader.load() 
documets = load_documents()

