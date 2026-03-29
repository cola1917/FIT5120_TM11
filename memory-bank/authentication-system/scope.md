# Authentication System
This task is to implement the simple authentication mechanism for accessing the back-end server API. The authentication system used shall be the OAuth2 with Password and Bearer flow. We are going to use FastAPI security utilities to get the username and password. OAuth2 specifies that when using the "password flow" (that we are using) the client/user must send a username and password fields as form data. And the spec says that the fields have to be named like that. So user-name or email wouldn't work. Since we are NOT allowed to store any user data in the back-end, the system will use a simple hardcoded username and password value to perform authentication. This is acceptable since the system will only be used for demo purposes. No need for scopes, all API endpoints shall be accessible with the auth token, no need to segregate by scopes.

## Front-end Changes
The mobile app shall obtain a auth token from the back-end server before calling any back-end API endpoints. The auth token shall be included in these API calls as a bearer token. The mobile app shall cache the token locally and reuse it when possible.

## Back-end Changes
The back-end server shall expose endpoints to allow callers to authenticate and obtain auth tokens. The authentication logic shall simply be a check that the username and password are the expected hardcoded values. The token returned should have a reasonable TTL.
