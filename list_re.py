import vertexai
from vertexai.preview import reasoning_engines
vertexai.init(project="elastic-496520", location="us-central1")
engines = reasoning_engines.ReasoningEngine.list()
for re in engines:
    print(f"Name: {re.resource_name}, Display: {re.display_name}")
