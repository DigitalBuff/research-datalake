# Best practices
- prefer lightweight versions of docker images (such as alpine)
- use environment variables for configuration values and secrets
- do not automatically generate new documentation
- keep documentation to the essentials
- don't mention configuration values in the documentation, so that their value is managed in one location and not scattered in documentation. Only mention configuration keys. Only the main README should have a summary of the local credentials to access the publicly exposed components.

# Python best practices
- keep imports at the top of the file
- put configuration values in a typed config class, and initialize it from environment variables
- use types