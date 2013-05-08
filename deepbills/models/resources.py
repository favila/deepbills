# encoding: utf-8
import deepbills as db
from functools import partial

# +root+                               # GET
# dashboard    (_type_)                # GET
# download                             # GET
# bills        '*'         (create)    # POST
# bills        [docid]                 # GET   PUT  (group:)
# bills        [docid]     (view)      # GET
# bills        [docid]     (edit)      # GET   POST (group:admin group:editor)
# vocabularies [vocabid]               # GET
# vocabularies [vocabid]  ?q           # GET

# locks                                # GET
# locks/user                           # GET (group:admin)   POST ()

# users                                # GET
# users         [userid]               # GET   POST (group:admin)  DELETE (group:admin)



# Resources and permissions
# Dashboard         view
# Download          view
# Bill              view  replace.text  replace.status
# Vocabularies      view
# Vocabulary        view  replace

# Users             view
# User              view edit.own edit.other delete
# Locks             view
# Lock              view delete edit.own edit.other 


class ResourceWrapper(object):
    """A location-aware wrapper for Resources

    Will automatically set name and parent of child resources if provided a mapping
    of children.
    """
    def __init__(self, name=None, parent=None, children=None, default=None,
                 childcallback=None, acl=()):
        """Set resource-related properties all at once

        This method is also available as _resource_properties() to modify after
        init.

        Arguments:

        +name+          String __name__ property of current resource
        +parent+        Object __parent__ property of the current resource
        +children+      Child resources--must provide a __getitem__
        +default+       Callable which returns a resource. Callable is
                        supplied a name and the parent (self), and must return
                        a child resource or None. IS CALLED ONLY IF +children+
                        RAISES KeyError!
        +childcallback+ Any found children will be run through this callback
                        and its return value will replace the found child.
        +acl+           Access control list (__acl__) of current resource
        """
        self.children = children if children is not None else {}
        self.default = default
        self.childcallback = childcallback
        self.__name__ = name
        self.__parent__ = parent
        self.__acl__ = acl

    def __getitem__(self, name):
        child = None
        try:
            child = self.children[name]
        except KeyError:
            if self.default is not None:
                child = self.default(name, self)
            else:
                raise

        if child is None:
            raise KeyError(name)

        if self.childcallback is not None:
            child = self.childcallback(child)


        child.__name__ = name
        child.__parent__ = self
        return child







def approot(request):
    root = {
        'dashboard':    db.BillList,
        'download':     db.Bills,
        'bills':        db.Bills,
        'vocabularies': db.Vocabularies,
        'users':        db.Users,
        'locks':        db.Locks,
    }
    ctor = lambda child, db=request.basex: child(db)
    return ResourceWrapper(children=root_with_db, childcallback=ctor)

    

