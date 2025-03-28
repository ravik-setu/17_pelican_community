from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    printer_name = fields.Char(string="Printer Name")
    iot_configuration_id = fields.Many2one('setu.iot.configuration',string="IOT")

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