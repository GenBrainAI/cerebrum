Authentication¶
Github supports various authentication methods. Depending on the entity that authenticates and the Github API endpoint being called, only a subset of methods is available.

All authentication methods require this import:

from github import Auth
from github import Github
from github import GithubIntegration
Login authentication¶
Users can authenticate by a login and password:

auth = Auth.Login("user_login", "password")
g = Github(auth=auth)
g.get_user().login
'user_login'
OAuth token authentication¶
Users can authenticate by a token:

auth = Auth.Token("access_token")
g = Github(auth=auth)
g.get_user().login
'login'
Netrc authentication¶
Write your credentials into a .netrc file:

machine api.github.com
login token
password <TOKEN>
You might need to create the environment variable NETRC with the path to this file.

Then, use a github.Auth.NetrcAuth instance to access these information:

auth = Auth.NetrcAuth()
g = Github(auth=auth)
g.get_user().login
'login'
App authentication¶
A Github Apps authenticate by an application id and a private key.

Note that there is only a limited set of endpoints that can be called when authenticated as a Github App. Instead of using github.Github, entry point github.GithubIntegration should be used when authenticated as a Github App:

auth = Auth.AppAuth(123456, private_key)
gi = GithubIntegration(auth=auth)
for installation in gi.get_installations():
    installation.id
'1234567'
Get a github.Github instance authenticated as an App installation:

installation = gi.get_installations()[0]
g = installation.get_github_for_installation()
g.get_repo("user/repo").name
'repo'
App installation authentication¶
A specific installation of a Github App can use the Github API like a normal user. It authenticates by the Github App authentication (see above) and the installation id. The AppInstallationAuth fetches an access token for the installation and handles its expiration timeout. The access token is refreshed automatically.

auth = Auth.AppAuth(123456, private_key).get_installation_auth(installation_id, token_permissions)
g = Github(auth=auth)
g.get_repo("user/repo").name
'repo'
Alternatively, the github.Github instance can be retrieved via github.GithubIntegration:

auth = Auth.AppAuth(123456, private_key)
gi = GithubIntegration(auth=auth)
g = gi.get_github_for_installation(installation_id, token_permissions)
g.get_repo("user/repo").name
'repo'
App user authentication¶
A Github App can authenticate on behalf of a user. For this, the user has to generate a user access token for a Github App. This process completes with a one-time code. Together with the client_id and client_secret of the app, a Github App user token can be generated once:

g = Github()
app = g.get_oauth_application(client_id, client_secret)
token = app.get_access_token(code)
Memorize the token.refresh_token, as only this can be used to create new tokens for this user. The token.token expires 8 hours, and the token.refresh_token expires 6 months after creation.

A token can be refreshed as follows. This invalidates the old token and old refresh token, and creates a new set of token and refresh tokens:

g = Github()
app = g.get_oauth_application(client_id, client_secret)
token = app.refresh_access_token(refresh_token)
You can authenticate with Github using this token:

auth = app.get_app_user_auth(token)
g = Github(auth=auth)
g.get_user().login
'user_login'
The auth instance will refresh the token automatically when auth.token is accessed.

Main Class¶
This is the main class.

Get current user¶
user = g.get_user()
user.login
u'sfdye'
Get user by name¶
user = g.get_user("sfdye")
user.name
u'Wan Liuyang'
Get repository by name¶
repo = g.get_repo("PyGithub/PyGithub")
repo.name
u'PyGithub'
Get organization by name¶
org = g.get_organization("PyGithub")
org.login
u'PyGithub'
Get enterprise consumed licenses by name¶
enterprise = g.get_enterprise_consumed_licenses("PyGithub")
enterprise_consumed_licenses = enterprise.get_enterprise_consumed_licenses()
enterprise_consumed_licenses.total_seats_consumed
5000
Search repositories by language¶
repositories = g.search_repositories(query='language:python')
for repo in repositories:
   print(repo)

Repository(full_name="vinta/awesome-python")
Repository(full_name="donnemartin/system-design-primer")
Repository(full_name="toddmotto/public-apis")
Repository(full_name="rg3/youtube-dl")
Repository(full_name="tensorflow/models")
Repository(full_name="django/django")
Search repositories based on number of issues with good-first-issue¶
repositories = g.search_repositories(query='good-first-issues:>3')
for repo in repositories:
   print(repo)

Repository(full_name="vuejs/vue")
Repository(full_name="facebook/react")
Repository(full_name="facebook/react-native")
Repository(full_name="electron/electron")
Repository(full_name="Microsoft/vscode")

Repository¶
Get repository topics¶
repo = g.get_repo("PyGithub/PyGithub")
repo.get_topics()
[u'pygithub', u'python', u'github', u'github-api']
Get count of stars¶
repo = g.get_repo("PyGithub/PyGithub")
repo.stargazers_count
2086
Get list of open issues¶
repo = g.get_repo("PyGithub/PyGithub")
open_issues = repo.get_issues(state='open')
for issue in open_issues:
    print(issue)

Issue(title="How to get public events?", number=913)
Issue(title="Prevent .netrc from overwriting Auth header", number=910)
Issue(title="Cache fetch responses", number=901)
Issue(title="Is suspended_users for github enterprise implemented in NamedUser?", number=900)
Issue(title="Adding migration api wrapper", number=899)
Get list of code scanning alerts¶
repo = g.get_repo("PyGithub/PyGithub")
codescan_alerts = repo.get_codescan_alerts()
for alert in codescan_alerts:
    print(alert.number, alert.created_at, alert.dismissed_at)
    print("  ", alert.tool.name, alert.tool.version, alert.tool.guid)
    print("  ", alert.rule.name alert.rule.security_severity_level alert.rule.severity)
    print("    ", alert.rule.description)
    print("  ", alert.most_recent_instance.ref, alert.most_recent_instance.state)
    print("    ", alert.most_recent_instance.location)
    print("    ", alert.most_recent_instance.message['text'])

3 1984-02-29 12:34:56 None
  CodeQL 2.6.1 None
  py/weak-sensitive-data-hashing high warning
    Use of a broken or weak cryptographic hashing algorithm on sensitive data
  refs/heads/master | open
    src/secrets/rats.py @ l42:c13-l42:c69
    Sensitive data (password) is used in a hashing algorithm (SHA1) that is insecure⤶
    for password hashing, since it is not a computationally expensive hash function.
Get all the labels of the repository¶
repo = g.get_repo("PyGithub/PyGithub")
labels = repo.get_labels()
for label in labels:
    print(label)

Label(name="Hacktoberfest")
Label(name="WIP")
Label(name="bug")
Label(name="documentation")
Get all of the contents of the root directory of the repository¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_contents("")
for content_file in contents:
    print(content_file)

ContentFile(path=".github")
ContentFile(path=".gitignore")
ContentFile(path="CONTRIBUTING.md")
ContentFile(path="COPYING")
ContentFile(path="COPYING.LESSER")
ContentFile(path="MAINTAINERS")
ContentFile(path="MANIFEST.in")
ContentFile(path="README.md")
ContentFile(path="doc")
ContentFile(path="github")
ContentFile(path="manage.sh")
ContentFile(path="requirements.txt")
ContentFile(path="scripts")
ContentFile(path="setup.py")
Get all of the contents of the repository recursively¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_contents("")
while contents:
    file_content = contents.pop(0)
    if file_content.type == "dir":
        contents.extend(repo.get_contents(file_content.path))
    else:
        print(file_content)

ContentFile(path=".gitignore")
ContentFile(path="CONTRIBUTING.md")
...
ContentFile(path="github/tests/ReplayData/Team.testRepoPermission.txt")
ContentFile(path="github/tests/ReplayData/Team.testRepos.txt")
ContentFile(path="github/tests/ReplayData/UserKey.setUp.txt")
Get a specific content file¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_contents("README.md")
print(contents)

ContentFile(path="README.md")
Create a new file in the repository¶
repo = g.get_repo("PyGithub/PyGithub")
repo.create_file("test.txt", "test", "test", branch="test")
{'content': ContentFile(path="test.txt"), 'commit': Commit(sha="5b584cf6d32d960bb7bee8ce94f161d939aec377")}
Update a file in the repository¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_contents("test.txt", ref="test")
repo.update_file(contents.path, "more tests", "more tests", contents.sha, branch="test")
{'commit': Commit(sha="b06e05400afd6baee13fff74e38553d135dca7dc"), 'content': ContentFile(path="test.txt")}
Delete a file in the repository¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_contents("test.txt", ref="test")
repo.delete_file(contents.path, "remove test", contents.sha, branch="test")
{'commit': Commit(sha="0f40b0b4f31f62454f1758d7e6b384795e48fd96"), 'content': NotSet}
Get the top 10 referrers over the last 14 days¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_top_referrers()
print(contents)
[
  Referrer(referrer="Google", count=4, uniques=3),
  Referrer(referrer="stackoverflow.com", count=2, uniques=2),
  Referrer(referrer="eggsonbread.com", count=1, uniques=1),
  Referrer(referrer="yandex.ru", count=1, uniques=1)
]
Get the top 10 popular contents over the last 14 days¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_top_paths()
print(contents)
[
  Path(path="/github/hubot", title="github/hubot: A customizable life embetterment robot.", count=3542, uniques=2225),
  Path(path="/github/hubot/blob/master/docs/scripting.md", title="hubot/scripting.md at master · github/hubot · GitHub", count=1707, uniques=804),
  Path(path="/github/hubot/tree/master/docs", title="hubot/docs at master · github/hubot · GitHub", count=685, uniques=435),
  Path(path="/github/hubot/tree/master/src", title="hubot/src at master · github/hubot · GitHub", count=577, uniques=347),
  Path(path="/github/hubot/blob/master/docs/index.md", title="hubot/index.md at master · github/hubot · GitHub", count=379, uniques=259),
  Path(path="/github/hubot/blob/master/docs/adapters.md", title="hubot/adapters.md at master · github/hubot · GitHub", count=354, uniques=201),
  Path(path="/github/hubot/tree/master/examples", title="hubot/examples at master · github/hubot · GitHub", count=340, uniques=260),
  Path(path="/github/hubot/blob/master/docs/deploying/heroku.md", title="hubot/heroku.md at master · github/hubot · GitHub", count=324, uniques=217),
  Path(path="/github/hubot/blob/master/src/robot.coffee", title="hubot/robot.coffee at master · github/hubot · GitHub", count=293, uniques=191),
  Path(path="/github/hubot/blob/master/LICENSE.md", title="hubot/LICENSE.md at master · github/hubot · GitHub", count=281, uniques=222)
]
Get number of clones and breakdown for the last 14 days¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_clones_traffic()
contents = repo.get_clones_traffic(per="week")
print(contents)
{
  "count": 173,
  "uniques": 128,
  "clones": [
    Clones(timestamp=2016-10-10 00:00:00, count=2, uniques=1),
    Clones(timestamp=2016-10-11 00:00:00, count=17, uniques=16),
    Clones(timestamp=2016-10-12 00:00:00, count=21, uniques=15),
    Clones(timestamp=2016-10-13 00:00:00, count=8, uniques=7),
    Clones(timestamp=2016-10-14 00:00:00, count=5, uniques=5),
    Clones(timestamp=2016-10-15 00:00:00, count=2, uniques=2),
    Clones(timestamp=2016-10-16 00:00:00, count=8, uniques=7),
    Clones(timestamp=2016-10-17 00:00:00, count=26, uniques=15),
    Clones(timestamp=2016-10-18 00:00:00, count=19, uniques=17),
    Clones(timestamp=2016-10-19 00:00:00, count=19, uniques=14),
    Clones(timestamp=2016-10-20 00:00:00, count=19, uniques=15),
    Clones(timestamp=2016-10-21 00:00:00, count=9, uniques=7),
    Clones(timestamp=2016-10-22 00:00:00, count=5, uniques=5),
    Clones(timestamp=2016-10-23 00:00:00, count=6, uniques=5),
    Clones(timestamp=2016-10-24 00:00:00, count=7, uniques=5)
  ]
}
Get number of views and breakdown for the last 14 days¶
repo = g.get_repo("PyGithub/PyGithub")
contents = repo.get_views_traffic()
contents = repo.get_views_traffic(per="week")
print(contents)
{
  "count": 14850,
  "uniques": 3782,
  "views": [
    View(timestamp=2016-10-10 00:00:00, count=440, uniques=143),
    View(timestamp=2016-10-11 00:00:00, count=1308, uniques=414),
    View(timestamp=2016-10-12 00:00:00, count=1486, uniques=452),
    View(timestamp=2016-10-13 00:00:00, count=1170, uniques=401),
    View(timestamp=2016-10-14 00:00:00, count=868, uniques=266),
    View(timestamp=2016-10-15 00:00:00, count=495, uniques=157),
    View(timestamp=2016-10-16 00:00:00, count=524, uniques=175),
    View(timestamp=2016-10-17 00:00:00, count=1263, uniques=412),
    View(timestamp=2016-10-18 00:00:00, count=1402, uniques=417),
    View(timestamp=2016-10-19 00:00:00, count=1394, uniques=424),
    View(timestamp=2016-10-20 00:00:00, count=1492, uniques=448),
    View(timestamp=2016-10-21 00:00:00, count=1153, uniques=332),
    View(timestamp=2016-10-22 00:00:00, count=566, uniques=168),
    View(timestamp=2016-10-23 00:00:00, count=675, uniques=184),
    View(timestamp=2016-10-24 00:00:00, count=614, uniques=237)
  ]
}
Mark the notifications of the repository as read¶
repo = g.get_repo("PyGithub/PyGithub")
repo.mark_notifications_as_read()

Branch¶
Get list of branches¶
repo = g.get_repo("PyGithub/PyGithub")
list(repo.get_branches())
[Branch(name="master")]
Note that the Branch object returned by get_branches() is not fully populated, and you can not query everything. Use get_branch(branch=”master”) once you have the branch name.

Get a branch¶
repo = g.get_repo("PyGithub/PyGithub")
repo.get_branch(branch="master")
Branch(name="master")
Get HEAD commit of a branch¶
branch = g.get_repo("PyGithub/PyGithub").get_branch("master")
branch.commit
Commit(sha="5e69ff00a3be0a76b13356c6ff42af79ff469ef3")
Get protection status of a branch¶
branch = g.get_repo("PyGithub/PyGithub").get_branch("master")
branch.protected
True
See required status checks of a branch¶
branch = g.get_repo("PyGithub/PyGithub").get_branch("master")
branch.get_required_status_checks()
RequiredStatusChecks(url="https://api.github.com/repos/PyGithub/PyGithub/branches/master/protection/required_status_checks", strict=True)


Commit¶
Create commit status check¶
# sha -> commit on which the status check will be created
# For example, for a webhook payload
# sha = data["pull_request"]["head"]["sha"]
repo.get_commit(sha=sha).create_status(
    state="pending",
    target_url="https://FooCI.com",
    description="FooCI is building",
    context="ci/FooCI"
)
Get commit date¶
commit = repo.get_commit(sha=sha)
print(commit.commit.author.date)
2018-10-11 03:04:52
print(commit.commit.committer.date)
2018-10-11 03:04:52


PullRequest¶
Create a new Pull Request¶
repo = g.get_repo("PyGithub/PyGithub")
body = '''
SUMMARY
Change HTTP library used to send requests

TESTS
  - [x] Send 'GET' request
  - [x] Send 'POST' request with/without body
'''
pr = repo.create_pull(base="master", head="develop", title="Use 'requests' instead of 'httplib'", body=body)
pr
PullRequest(title="Use 'requests' instead of 'httplib'", number=664)
Get Pull Request by Number¶
repo = g.get_repo("PyGithub/PyGithub")
pr = repo.get_pull(664)
pr
PullRequest(title="Use 'requests' instead of 'httplib'", number=664)
Get Pull Requests by Query¶
repo = g.get_repo("PyGithub/PyGithub")
pulls = repo.get_pulls(state='open', sort='created', base='master')
for pr in pulls:
   print(pr.number)

400
861
875
876
Add and modify Pull Request comment¶
repo = g.get_repo("PyGithub/PyGithub")
pr = repo.get_pull(2390)
last_commit = pr.get_commits()[pr.commits - 1]
comment = pr.create_comment("This is a comment", last_commit, "file.txt", 0)
comment
PullRequestComment(user=NamedUser(login="anonymous"), id=1057297855)
comment.body
'This is a comment'
comment.edit("This is a modified comment")
comment.body
'This is a modified comment'


Issues¶
Get issue¶
repo = g.get_repo("PyGithub/PyGithub")
repo.get_issue(number=874)
    Issue(title="PyGithub example usage", number=874)
Create comment on issue¶
repo = g.get_repo("PyGithub/PyGithub")
issue = repo.get_issue(number=874)
issue.create_comment("Test")
    IssueComment(user=NamedUser(login="user"), id=36763078)
Create issue¶
repo = g.get_repo("PyGithub/PyGithub")
repo.create_issue(title="This is a new issue")
    Issue(title="This is a new issue", number=XXX)
Create issue with body¶
repo = g.get_repo("PyGithub/PyGithub")
repo.create_issue(title="This is a new issue", body="This is the issue body")
    Issue(title="This is a new issue", number=XXX)
Create issue with labels¶
repo = g.get_repo("PyGithub/PyGithub")
label = repo.get_label("My Label")
repo.create_issue(title="This is a new issue", labels=[label])
    Issue(title="This is a new issue", number=XXX)
Create issue with assignee¶
repo = g.get_repo("PyGithub/PyGithub")
repo.create_issue(title="This is a new issue", assignee="github-username")
    Issue(title="This is a new issue", number=XXX)
Create issue with milestone¶
repo = g.get_repo("PyGithub/PyGithub")
milestone = repo.create_milestone("New Issue Milestone")
repo.create_issue(title="This is a new issue", milestone=milestone)
    Issue(title="This is a new issue", number=XXX)
Close all issues¶
repo = g.get_repo("PyGithub/PyGithub")
open_issues = repo.get_issues(state='open')
for issue in open_issues:
    issue.edit(state='closed')


Milestone¶
Get Milestone list¶
repo = g.get_repo('PyGithub/PyGithub')
open_milestones = repo.get_milestones(state='open')
for milestone in open_milestones:
   print(milestone)

Milestone(number=1)
Milestone(number=2)
Get Milestone¶
repo = g.get_repo('PyGithub/PyGithub')
repo.get_milestone(number=1)
Milestone(number=1)
Create Milestone¶
repo = g.get_repo('PyGithub/PyGithub')
repo.create_milestone(title='New Milestone')
Milestone(number=1)
Create Milestone with State and Description¶
repo = g.get_repo('PyGithub/PyGithub')
repo.create_milestone(title='New Milestone', state='open', description='Milestone description')
Milestone(number=1)


Webhook¶
Creating and Listening to Webhooks with PyGithub and Pyramid¶
To receive a continuous stream of events, one can set up a wsgiref app using Pyramid to handle incoming POST requests.

The below code sets up a listener which creates and utilizes a webhook. Using ‘pull_request’ and ‘push’ for the EVENT attributes, any time a PR is opened, closed, merged, or synced, or a commit is pushed, Github sends a POST containing a payload with information about the PR/push and its state.

The below example was drawn largely from Github’s Examples on working with Webhooks. A list of all applicable event types for Webhooks can be found in Github’s documentation

from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.view import view_config, view_defaults
from pyramid.response import Response
from github import Github

ENDPOINT = "webhook"

@view_defaults(
    route_name=ENDPOINT, renderer="json", request_method="POST"
)
class PayloadView(object):
    """
    View receiving of Github payload. By default, this view it's fired only if
    the request is json and method POST.
    """

    def __init__(self, request):
        self.request = request
        # Payload from Github, it's a dict
        self.payload = self.request.json

    @view_config(header="X-Github-Event:push")
    def payload_push(self):
        """This method is a continuation of PayloadView process, triggered if
        header HTTP-X-Github-Event type is Push"""
        print("No. commits in push:", len(self.payload['commits']))
        return Response("success")

    @view_config(header="X-Github-Event:pull_request")
    def payload_pull_request(self):
        """This method is a continuation of PayloadView process, triggered if
        header HTTP-X-Github-Event type is Pull Request"""
        print("PR", self.payload['action'])
        print("No. Commits in PR:", self.payload['pull_request']['commits'])

        return Response("success")

    @view_config(header="X-Github-Event:ping")
    def payload_else(self):
        print("Pinged! Webhook created with id {}!".format(self.payload["hook"]["id"]))
        return {"status": 200}


def create_webhook():
    """ Creates a webhook for the specified repository.

    This is a programmatic approach to creating webhooks with PyGithub's API. If you wish, this can be done
    manually at your repository's page on Github in the "Settings" section. There is a option there to work with
    and configure Webhooks.
    """

    USERNAME = ""
    PASSWORD = ""
    OWNER = ""
    REPO_NAME = ""
    EVENTS = ["push", "pull_request"]
    HOST = ""

    config = {
        "url": "http://{host}/{endpoint}".format(host=HOST, endpoint=ENDPOINT),
        "content_type": "json"
    }

    g = Github(USERNAME, PASSWORD)
    repo = g.get_repo("{owner}/{repo_name}".format(owner=OWNER, repo_name=REPO_NAME))
    repo.create_hook("web", config, EVENTS, active=True)


if __name__ == "__main__":
    config = Configurator()

    create_webhook()

    config.add_route(ENDPOINT, "/{}".format(ENDPOINT))
    config.scan()

    app = config.make_wsgi_app()
    server = make_server("0.0.0.0", 80, app)
    server.serve_forever()
Outputs from a server configured as above:

x.y.w.z - - [15/Oct/2018 23:49:19] "POST /webhook HTTP/1.1" 200 15
Pinged! Webhook created with id <redacted id>!
No. commits in push: 1
x.y.w.z - - [15/Oct/2018 23:49:32] "POST /webhook HTTP/1.1" 200 7
PR synchronize
x.y.w.z - - [15/Oct/2018 23:49:33] "POST /webhook HTTP/1.1" 200 7
No. Commits in PR: 10
PR closed
x.y.w.z - - [15/Oct/2018 23:49:56] "POST /webhook HTTP/1.1" 200 7
No. Commits in PR: 10
x.y.w.z - - [15/Oct/2018 23:50:00] "POST /webhook HTTP/1.1" 200 7
PR reopened
No. Commits in PR: 10


