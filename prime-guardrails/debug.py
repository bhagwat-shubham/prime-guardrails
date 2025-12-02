from agent import root_agent

print("\n--- AGENT METHODS ---")
# This prints all available methods on your agent object
print([d for d in dir(root_agent) if not d.startswith('_')])
print("---------------------\n")