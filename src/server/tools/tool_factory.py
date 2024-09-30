from src.server.controllers.curried_proxy import CurriedProxy
from src.server.tools.file_tool import FileTool
from src.server.tools.github_tool import GithubTool
from src.server.tools.jira_tool import fetch_jira_tickets


class ToolFactory:
    def __init__(self, name: str, curried_proxy: CurriedProxy):
        tools: dict = {
            'save_file': FileTool,
            'fetch_jira_tickets': fetch_jira_tickets,
            'GithubTool': GithubTool('access_token', 'repo_name')
        }
        self.tool = tools[name]
        self.name = name
        self.curried_proxy = curried_proxy

    def set_curried_proxy(self):
        return self.curried_proxy.add_tool(self.name, self.tool)