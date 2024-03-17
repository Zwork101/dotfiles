import os
import shutil
import sublime

from textwrap import dedent

from .icons import icons_json_content
from .utils import path
from .utils.logging import log, dump

__all__ = ["check", "enable", "disable"]

HAS_FIND_SYNTAX = hasattr(sublime, "list_syntaxes")

EMPTY_TEMPLATE = dedent(
    """
    %YAML 1.2
    ---
    name: {0}
    scope: {1}
    hidden: true
    file_extensions:
      - {2}
    contexts:
      main: []
    """
).lstrip()

if int(sublime.version()) > 4075:
    MAIN_TEMPLATE = dedent(
        """
        %YAML 1.2
        ---
        name: {0}
        scope: {1}
        hidden: true
        file_extensions:
          - {2}
        contexts:
          main:
            - include: scope:{3}
              apply_prototype: true
        """
    ).lstrip()

else:
    MAIN_TEMPLATE = dedent(
        """
        %YAML 1.2
        ---
        name: {0}
        scope: {1}
        hidden: true
        file_extensions:
          - {2}
        contexts:
          main:
            - include: scope:{3}#prototype
            - include: scope:{3}
        """
    ).lstrip()


def check(desired_state):
    if desired_state:
        enable()
    else:
        disable()


def disable():
    log("Disabling aliases")

    def delete_alias_files(syntaxes):
        base_syntaxes = None
        for syntax in syntaxes:
            if HAS_FIND_SYNTAX:
                base_syntaxes = sublime.find_syntax_by_scope(
                    syntax.get("base", "text.plain")
                )
            if base_syntaxes:
                delete_alias_file(syntax, base_syntaxes[0].path)
            else:
                delete_alias_file(syntax, "Plain text.tmLanguage")

    for file_type in icons_json_content().values():
        delete_alias_files(file_type.get("aliases", []))
        delete_alias_files(file_type.get("syntaxes", []))

    shutil.rmtree(path.overlay_aliases_path(), ignore_errors=True)
    shutil.rmtree(path.overlay_cache_path(), ignore_errors=True)


def enable():
    if HAS_FIND_SYNTAX:
        # Built a dict of { scope: syntax } from visible/real syntaxes.
        # Note: Existing aliases in the overlay are hidden and thus excluded
        #       by default. Also ignore possible aliases or special purpose
        #       syntaxes from 3rd-party packages.
        real_syntaxes = {
            s.scope: s.path for s in sublime.list_syntaxes() if not s.hidden
        }
    else:
        real_syntaxes = {}

    def real_syntax_for(selector):
        for scope in selector.split(","):
            real_syntax = real_syntaxes.get(scope.strip())
            if real_syntax:
                return real_syntax
        return None

    def check_alias_files(syntaxes):
        for syntax in syntaxes:
            real_syntax = real_syntax_for(syntax["scope"])
            if real_syntax:
                delete_alias_file(syntax, real_syntax)
            elif "extensions" in syntax:
                create_alias_file(syntax)

    try:
        os.makedirs(path.overlay_aliases_path())
    except FileExistsError:
        log("Updating aliases")
    else:
        log("Enabling aliases")

    for file_type in icons_json_content().values():
        check_alias_files(file_type.get("aliases", []))
        if HAS_FIND_SYNTAX:
            check_alias_files(file_type.get("syntaxes", []))


def create_alias_file(alias):
    name = alias["name"]
    scope = alias["scope"].split(",", 1)[0]
    exts = "\n  - ".join(alias["extensions"])
    base = alias.get("base")

    alias_path = path.overlay_aliases_path(name + ".sublime-syntax")
    try:
        with open(alias_path, "x", encoding="utf-8") as out:
            if base:
                out.write(MAIN_TEMPLATE.format(name, scope, exts, base))
            else:
                out.write(EMPTY_TEMPLATE.format(name, scope, exts, base))
    except FileExistsError:
        pass
    except Exception as error:
        dump("+ {}.sublime-syntax | {}".format(name, error))
    else:
        dump("+ {}.sublime-syntax".format(name))


def delete_alias_file(alias, real_syntax):
    alias_name = alias["name"] + ".sublime-syntax"
    alias_path = path.overlay_aliases_path(alias_name)
    if not os.path.exists(alias_path):
        return

    # reassign real syntax to any open view, which uses the alias
    alias_resource = path.overlay_aliases_resource_path(alias_name)
    for window in sublime.windows():
        for view in window.views():
            syntax = view.settings().get("syntax")
            if syntax and syntax == alias_resource:
                view.assign_syntax(real_syntax)

    # actually delete the alias syntax
    try:
        os.remove(alias_path)
    except Exception as error:
        dump("- {} | {}".format(alias_name, error))
    else:
        dump("- {}".format(alias_name))
