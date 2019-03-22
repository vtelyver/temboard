import logging
from os import path
import tornado.web
from tornado.escape import url_escape, url_unescape

from temboardui.web import (
    Blueprint,
    HTTPError,
    Redirect,
    TemplateRenderer,
)


logger = logging.getLogger(__name__)
blueprint = Blueprint()
blueprint.generic_proxy("/pgconf/configuration", methods=["POST"])
plugin_path = path.dirname(path.realpath(__file__))
render_template = TemplateRenderer(plugin_path + "/templates")


def configuration(config):
    return {}


def get_routes(config):
    routes = blueprint.rules + [
        tornado.web.url(
            r"/js/pgconf/(.*)",
            tornado.web.StaticFileHandler,
            {'path': plugin_path + "/static/js"}
        ),
        tornado.web.url(
            r"/css/pgconf/(.*)",
            tornado.web.StaticFileHandler,
            {'path': plugin_path + "/static/css"}
        ),
    ]
    return routes


@blueprint.instance_route("/pgconf/configuration(?:/category/(.+))?",
                          methods=["GET", "POST"])
def configuration_handler(request, category=None):
    request.instance.check_active_plugin(__name__)
    profile = request.instance.get_profile()
    agent_username = profile['username']
    template_vars = {}
    # Deduplicate HTTP prefix of plugin on agent.
    prefix = "/pgconf/configuration"
    query_filter = request.handler.get_argument('filter', None, strip=True)

    if "GET" == request.method:
        status = request.instance.get(prefix + "/status")
        categories = request.instance.get(prefix + "/categories")

        if query_filter:
            query = {'filter': query_filter}
            configuration_url = prefix
        else:
            if category:
                category = url_unescape(category)
            else:
                category = categories['categories'][0]
            logger.debug("category=%s", category)
            query = {}
            configuration_url = prefix + "/category/" + url_escape(category)
        configuration = request.instance.get(configuration_url, query=query)
    else:
        settings = {'settings': [
            {'name': name, 'setting': value[0]}
            for name, value in request.arguments.iteritems()
            # 'filter' is not a setting, just ignore it.
            if name != 'filter'
        ]}
        try:
            request.instance.post(prefix, body=settings)
            # Redirect to GET page, same URI.
            return Redirect(request.uri)
        except HTTPError as e:
            # Rerender HTML page with errors.
            template_vars['error_code'] = e
            template_vars['error_message'] = e.log_message

    return render_template(
        'configuration.html',
        nav=True,
        role=request.current_user,
        instance=request.instance,
        agent_username=agent_username,
        plugin=__name__,
        xsession=request.instance.xsession,
        current_cat=category,
        configuration_categories=categories,
        configuration_status=status,
        data=configuration,
        query_filter=query_filter,
        **template_vars
    )
