# -*- coding: utf-8 -*-
from textwrap import TextWrapper, dedent
from cmd import Cmd

from bravo.packets import make_packet

"""
the shell for the proxy.


"""

wrap = 20

# wrap around stdout
class ChatWrapper(object):
    def __init__(self, stdout):
        self.stdout = stdout

    def write(self, text):
        """
        Send text back to the client.
        """

        for line in text.strip().split("\n"):
            line = line[:100]
            self.stdout.write(make_packet("chat", message=line))

class ProxyShell(Cmd):
    def __init__(self, proxy, stdout):
        Cmd.__init__(self)
        self.proxy = proxy
        self.stdout = ChatWrapper(stdout)
        self.wrap = wrap

        # a wrapper...not implimented
        wrapper = TextWrapper(width=self.wrap)


    def do_add(self, line):
        """
        Add a plugin to the proxy.
        Usage: add [plugin name]
        """
        pass

    def do_remove(self, line):
        """
        Remove a plugin from the proxy.
        Usage: remove [plugin]
        """
        pass

    def do_enable(self, line):
        """
        Enable a plugin.
        Usage: enable [plugin]
        
        Plugin must already be added.
        """
        pass

    def do_disable(self, line):
        """
        Disable a plugin.
        Usage: disable [plugin]

        Plugin must laready be added.
        """
        pass

    def do_set(self, line):
        """
        Set a plugin's variable.
        Usage: set [plugin] [variable] [value]
        """
        pass

    def do_show(self, line):
        """
        Show a plugin's variable.
        Usage show [plugin] [variable]

        If the variable is ommited, then all the variable will be shown.
        """
        pass

    def do_reload(self, line):
        """
        Reload configuration files and scripts.
        Usage: reload

        not implimented
        """

    def do_status(self, line):
        """
        List plugins and status.
        Usage: list
        """
        def make_status(plugin):
            if plugin.enabled:
                return "on"
            elif not plugin.enabled:
                return "off"
            else:
                return "--"

        p = [ "%s %s" % (p.__class__, make_status(p)) for p in self.proxy.plugins ]
        self.print_topics("Plugins", p, 15,self.wrap)

    def do_quit(self, line):
        """
        Quit (not implimented)
        Usage: quit
        """
        self.proxy.transport.loseConnection()

    def emptyline(self):
        return ""

    def formatdoc(self, text):
        text = dedent(text)

        #remove initial newline
        if text[0] =="\n":
            text = text[1:]
        return text

    # overloaded to dedent leading tabs on doc strings
    def do_help(self, arg):
        """
        Get help
        Usage: help [topic]
        """
        if arg:
            # XXX check arg syntax
            try:
                func = getattr(self, 'help_' + arg)
            except AttributeError:
                try:
                    doc=getattr(self, 'do_' + arg).__doc__
                    if doc:
                        doc = self.formatdoc(doc)
                        self.stdout.write("%s\n"%str(doc))
                        return
                except AttributeError:
                    pass
                self.stdout.write("%s\n"%str(self.nohelp % (arg,)))
                return
            func()
        else:
            names = self.get_names()
            cmds_doc = []
            cmds_undoc = []
            help = {}
            for name in names:
                if name[:5] == 'help_':
                    help[name[5:]]=1
            names.sort()
            # There can be duplicates if routines overridden
            prevname = ''
            for name in names:
                if name[:3] == 'do_':
                    if name == prevname:
                        continue
                    prevname = name
                    cmd=name[3:]
                    if cmd in help:
                        cmds_doc.append(cmd)
                        del help[cmd]
                    elif getattr(self, name).__doc__:
                        cmds_doc.append(cmd)
                    else:
                        cmds_undoc.append(cmd)
            self.stdout.write("%s\n"%str(self.doc_leader))
            self.print_topics(self.doc_header,   cmds_doc,   15,self.wrap)
            self.print_topics(self.misc_header,  help.keys(),15,self.wrap)
            self.print_topics(self.undoc_header, cmds_undoc, 15,self.wrap)

