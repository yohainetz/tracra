import webbrowser
from oauth.oauth2 import GeneratePermissionUrl, GenerateOAuth2String, AuthorizeTokens

GOOGLE_CLIENT_ID = "711216531075-m4v8b6u5tjp0v8vvmakmbh5548e2el5q.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "w8VAI0Xswlpch1byUSdbr5Xj"



def openOauthWebsite():
    url = GeneratePermissionUrl(GOOGLE_CLIENT_ID)
    webbrowser.open(url)


def generateOauthString(authorization_code, email):

    response = AuthorizeTokens(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
                               authorization_code)
    refresh_token = response['refresh_token']
    access_token = response['access_token']

    auth_string = GenerateOAuth2String(email, access_token,
                         base64_encode=False)

    return access_token