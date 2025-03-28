import json
import logging

import werkzeug.exceptions
from werkzeug.urls import url_parse

from odoo import http
from odoo.http import content_disposition, request
from odoo.tools.misc import html_escape
from odoo.tools.safe_eval import safe_eval, time
import paramiko
from scp import SCPClient
from odoo.addons.web.controllers.report import ReportController

_logger = logging.getLogger(__name__)
import base64


class ReportController(ReportController):

    @http.route(['/report/download'], type='http', auth="user")
    def report_download(self, data, context=None, token=None):  # pylint: disable=unused-argument
        """This function is used by 'action_manager_report.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with an attachment header

        """

        requestcontent = json.loads(data)
        url, type_ = requestcontent[0], requestcontent[1]
        reportname = '???'
        try:
            if type_ in ['qweb-pdf', 'qweb-text']:
                converter = 'pdf' if type_ == 'qweb-pdf' else 'text'
                extension = 'pdf' if type_ == 'qweb-pdf' else 'txt'

                pattern = '/report/pdf/' if type_ == 'qweb-pdf' else '/report/text/'
                reportname = url.split(pattern)[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter=converter, context=context)
                else:
                    # Particular report:
                    data = url_parse(url).decode_query(cls=dict)  # decoding the args represented in JSON
                    if 'context' in data:
                        context, data_context = json.loads(context or '{}'), json.loads(data.pop('context'))
                        context = json.dumps({**context, **data_context})
                    response = self.report_routes(reportname, converter=converter, context=context, **data)

                report = request.env['ir.actions.report']._get_report_from_name(reportname)
                filename = "%s.%s" % (report.name, extension)

                if docids:
                    ids = [int(x) for x in docids.split(",") if x.isdigit()]
                    obj = request.env[report.model].browse(ids)
                    if report.print_report_name and not len(obj) > 1:
                        report_name = safe_eval(report.print_report_name, {'object': obj, 'time': time})
                        filename = "%s.%s" % (report_name, extension)
                response.headers.add('Content-Disposition', content_disposition(filename))
                try:
                    self.print_report_in_printer(response, report, filename)
                except Exception as e:
                    _logger.warning("Error {} comes at the time of printing report via printer {}, User {}".format(e,
                                                                                                                   request.env.user.printer_name,
                                                                                                                   request.env.user.name))
                return response
            else:
                return
        except Exception as e:
            _logger.warning("Error while generating report %s", reportname, exc_info=True)
            se = http.serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            res = request.make_response(html_escape(json.dumps(error)))
            raise werkzeug.exceptions.InternalServerError(response=res) from e


    def print_report_in_printer(self, response, report, filename):
        def create_ssh_client(server, port, user, password):
            client = paramiko.SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(server, port, user, password)
            return client

        def send_file(ssh_client, local_file, remote_file):
            with SCPClient(ssh_client.get_transport()) as scp:
                scp.put(local_file, remote_file)

        def execute_command(ssh_client, command):
            stdin, stdout, stderr = ssh_client.exec_command(command)
            print(stdout.read().decode())
            print(stderr.read().decode())

        configuration = request.env.user.iot_configuration_id
        if configuration and report.id in configuration.report_ids.ids:
            # Connection details
            server = configuration.server
            port = configuration.server_port
            user = configuration.server_user
            password = configuration.server_pass
            print()

            # filename = 'test12.txt'
            with open('/tmp/%s' % (filename), "wb") as fl:
                fl.write(response.data)
            fl.close()

            # File details
            local_file = '/tmp/%s' % (filename)
            remote_file = '/tmp/%s' % (filename)

            # Command to execute
            command = f"python3 /home/setu/Downloads/test.py '{request.env.user.printer_name}' '/tmp/{filename}'"

            # Create SSH client
            ssh_client = create_ssh_client(server, port, user, password)

            # Send file
            send_file(ssh_client, local_file, remote_file)

            # Execute command
            printer_response = execute_command(ssh_client, command)
            ssh_client.close()
            return printer_response