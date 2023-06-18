Contributing
----------------------------------

1. File an issue to notify the maintainers about what you're working on.
2. Fork the repo, develop and test your code changes.
3. Make sure that your commit messages clearly describe the changes.
4. Send a pull request.

File an Issue
----------------------------------

Use the issue tracker to start the discussion. It is possible that someone
else is already working on your idea, your approach is not quite right, or that
the functionality exists already. The ticket you file in the issue tracker will
be used to hash that all out.

Style Guide
-------------------
- [PEP8 as our style guide base.](https://peps.python.org/pep-0008/)
- [Black](https://github.com/psf/black) with `--line-length 120` instead of native 88.
- Comments and docstrings should aim to be 79 characters per line.
- Type hinting should be used for function declarations but not variable declarations.
- Keyword arguments are preferred for function calls even when the keyword is the same variable name as the function parameter.
- Imports should be in the following order: standard library imports, 3rd party dependency imports, and current project imports with a newline between each category of imports. 
- `import <module>` lines should come before `from <module> import <object>` lines.
- There should be 2 newlines before and after global variables: after the last import and before the first class or function declaration.
- When breaking out of a function with a return, avoid returning nothing.
- Each function should have a brief docstring explaining what the function is doing. 
  - The starting `"""` and ending `"""` should be on lines by themselves even for one-line docstrings.
  - Docstrings should be written as sentences with proper capitalization, grammar, and punctuation.
  - Specifying parameters or return type in a docstring isn't necessary because we use type hinting.
- Comments should be minimal and explain why the code is doing something instead of what it is doing.
- Any messages logged to console should not contain ending punctuation.
- Any settings, keys, values, or IDs that may change on a deployment basis should be kept in the config file.
- All Discord commands and command parameters should have descriptions.
- All Discord commands should start with `await ctx.defer()` to avoid 3 second timeouts.


Make the Pull Request
---------------------

- Once you have made all your changes, make a pull request to move everything back into the master branch of the Chiya. Be sure to reference the original issue in the pull request. Expect some back-and-forth with regards to style and compliance of these rules.
- Commits should be using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) formatting.
