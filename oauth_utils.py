import webbrowser
from oauth.oauth2 import GeneratePermissionUrl, GenerateOAuth2String, AuthorizeTokens
from utils_resource import ResourceManager

google_secret_filepath = ResourceManager().get_res_path(["tracra_resources","google_client.txt"])
try:
    google_secret_file = open(google_secret_filepath, "r", encoding="utf-8")
    GOOGLE_CLIENT_ID = google_secret_file.readline().strip() # first line
    GOOGLE_CLIENT_SECRET = google_secret_file.readline().strip() # second line
except Exception as e:
    print("Error when trying to read google secret")
    print(e)


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