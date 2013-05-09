from pyramid.config import Configurator
from models.deepbills import User
from models.resources import approot
from pyramid.authentication import BasicAuthAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import NO_PERMISSION_REQUIRED

# URL structure:

# /
# /query
# /search

# {docid} = {congress}{type}{number}{status}[-{rev}]
# {congress} = \d+
# {type} = hr
# {number} = \d+
# {status} = ih
# {rev}  = \d+ >= 1

# /bills/{docid} #GET, PUT, POST, DELETE
# /bills/{docid}/view
# /bills/{docid}/edit

# /activity
# /activity/users
# /activity/users/{userid}
# /activity/bills/{docid}

# /users/{userid}

# /vocabularies/{vocab} ?q=""
# /vocabularies/{vocab}/{vocabid}



def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    httpauthpolicy = BasicAuthAuthenticationPolicy(User.authentication_check, 'deepbills')

    config = Configurator(settings=settings)
    # make request.basex available
    config.add_tween('deepbills.models.BaseXClient2.basexsession_tween_factory')

    # set up auth
    config.set_authentication_policy(httpauthpolicy)
    config.set_authorization_policy(ACLAuthorizationPolicy())
    config.set_default_permission(NO_PERMISSION_REQUIRED)
    config.set_root_factory(approot)


    config.add_route('bill_types', '/')
    config.add_route('query', '/query')
    config.add_route('download', '/download')
    config.add_route('logout', '/logout')


    config.add_static_view('Editor', 'static/AKN/Editor')
    config.add_route('akn_editor', 'Editor/Index.html')
    config.add_static_view('static', 'static', cache_max_age=3600)


    config.scan()
    return config.make_wsgi_app()
