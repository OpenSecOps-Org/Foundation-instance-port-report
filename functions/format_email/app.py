import os

EMAIL_SIGNEE = os.environ['EMAIL_SIGNEE']


def lambda_handler(blob, _context):
    data = blob['Data']
    toc = {'red': [], 'other': []}

    subject = "Periodic Report on EC2 Port Exposure"

    style = "<style>"
    style += "table, th, td {border: 1px solid grey; border-collapse: collapse;}\n"
    style += "th, td {padding: 3px;}\n"
    style += "</style>"

    body = f"<html><head>{style}</head><body>"
    body += f"<h1 style='text-align:center'>{subject}</h1>"
    body += f"<h4 style='text-align:center'>from {EMAIL_SIGNEE}</h4>"

    body += '<div><TOC_PLACEHOLDER></div'

    for account_data in data:
        for region_data in account_data:
            if region_data:
                account_id = region_data['AccountId']
                account_name = region_data['AccountName']
                region = region_data['Region']
                body += f'<div id="{account_id}_{region}" class="AccountRegion">'
                body += "<hr>"
                body += f"<h2 style='text-align:center'>{account_id}, {account_name}</h2>"
                body += f"<h3 style='text-align:center'>{region}</h3>"
                html = format_data(region_data)
                add_to_toc(toc, html, account_id, account_name, region)
                body += html
                body += "</div>"

    body += "</body></html>"

    body = body.replace('<TOC_PLACEHOLDER>', format_toc(toc), 1)

    result = {
        "Subject": subject,
        "Body": body
    }

    return result


def add_to_toc(toc, html, account_id, account_name, region):
    if 'color:red' in html:
        toc['red'].append(
            f'<a style="white-space:nowrap" href="#{account_id}_{region}">{account_id} ({account_name}) {region}</a>'
        )
    else:
        toc['other'].append(
            f'<a style="white-space:nowrap" href="#{account_id}_{region}">{account_id} ({account_name}) {region}</a>'
        )


def format_toc(toc):
    result = '<h2>Table of Contents</h2>'

    if toc['red'] != []:
        result += '<div>'
        result += '<h3>To Investigate</h3>'
        result += '<ul>'
        for link in toc['red']:
            result += f'<li>{link}</li>'
        result += '</ul>'
        result += '</div>'

    if toc['other'] == []:
        return result

    result += '<div>'
    result += '<h3>No Remarks</h3>'
    for link in toc['other']:
        result += link + '&nbsp;&nbsp;&nbsp;&nbsp;'
    result += '</div>'

    return result


def format_data(data):
    instances = list(data['Instances'].items())
    security_groups = data['SecurityGroups']
    result = ""

    result += '<div class="Instances">'
    result += "<h3>Instances</h3>"
    result += '<table style="width:100%"><tr><th>Id</th><th>Name</th><th>Private IP</th><th>Public IP</th><th>Security Groups</th></tr>'
    for instance in instances:
        result += format_instance(instance)
    result += "</table></div><br><br>"

    result += '<div class="SecurityGroups">'
    result += "<h3>Security Group Ingress Rules</h3>"
    for security_group in security_groups:
        result += format_security_group(security_group, len(instances))
    result += "</div>"

    return result


def format_instance(i_t):
    i_id, data = i_t
    name = data.get('Name', False)
    sec_groups = data.get('SecurityGroups', False)
    private_ip = data.get('PrivateIp', False)
    public_ip = data.get('PublicIp', False)

    result = ""
    result += '<tr>'
    result += f"<td>{i_id}</td>"

    if name:
        result += f"<td>{name}</td>"
    else:
        result += "<td></td>"

    if private_ip:
        result += f"<td>{private_ip}</td>"
    else:
        result += "<td></td>"

    if public_ip:
        result += f"<td style=\"color:red\">{public_ip}</td>"
    else:
        result += "<td></td>"

    if sec_groups:
        result += '<td>'
        result += ',<br>'.join(sec_groups)
        result += '</td>'
    else:
        result += '<td style="color:red">NONE</td>'

    result += "</tr>"
    return result


def format_security_group(s_t, n_instances):
    sg_id, data = s_t
    name = data.get('Name', '')
    desc = data.get('Description', '')
    perms = data.get('IpPermissions', [])
    instances = data.get('Instances', [])

    id_rowspan = calculate_total_rows(desc, perms)

    result = ""
    result += '<div class="SecurityGroup">'
    result += '<table style="width:100%"><tr><th>Id</th><th>Proto</th><th>Ports</th><th>IP Ranges</th><th>Description</th></tr>'

    result += f"<tr><td rowspan=\"{id_rowspan}\">{sg_id}</td><td colspan=\"4\" style='text-align:center'>{name}</td></tr>"

    if desc != '':
        result += f"<tr><td colspan=\"4\" style='text-align:center'>{desc}</td></tr>"

    if instances != []:
        if len(instances) == n_instances:
            result += "<tr><td colspan=\"4\" style='text-align:center'>Used by all instances</td></tr>"
        else:
            inst_list = ', '.join(instances)
            result += f"<tr><td colspan=\"4\" style='text-align:center'>Used by {inst_list}</td></tr>"

    if perms == []:
        result += "<tr><td colspan=\"4\" style=\"color:red\">Permissions: None</td></tr>"
    else:
        for perm in perms:
            result += format_permission(perm)

    result += "</table></div><br><br>"
    return result


def format_permission(perm):
    ip_protocol = perm.get('IpProtocol')
    from_port = perm.get('FromPort', False)
    to_port = perm.get('ToPort', False)
    ip_ranges = perm.get('IpRanges', [])
    ip_v6_ranges = perm.get('Ipv6Ranges', [])
    user_id_group_pairs = perm.get('UserIdGroupPairs', False)

    desc = ''
    ports = ''
    result = ''

    if from_port:
        if from_port == to_port:
            ports = from_port
        else:
            ports = f"{from_port}-{to_port}"

    n_ranges = len(ip_ranges)

    if user_id_group_pairs and n_ranges == 0 and ip_v6_ranges == []:
        result += f"<tr><td>{ip_protocol}</td><td>{ports}</td><td colspan=\"2\"><i>IP-less internal</i></td></tr>"
        return result

    if n_ranges == 0:
        result += f"<tr><td>{ip_protocol}</td><td>{ports}</td><td colspan=\"2\" style=\"color:red\">No IP ranges</td></tr>"
        return result

    first_row = True
    for ip_range in ip_ranges:
        cidr_ip = ip_range.get('CidrIp')
        desc = ip_range.get('Description', '')
        style = ' style="color:red"' if cidr_ip == '0.0.0.0/0' else ''
        if first_row:
            result += f"<tr><td rowspan=\"{n_ranges}\">{ip_protocol}</td><td rowspan=\"{n_ranges}\">{ports}</td>"
            result += f"<td{style}>{cidr_ip}</td><td>{desc}</td></tr>"
            first_row = False
        else:
            result += f"<tr><td{style}>{cidr_ip}</td><td>{desc}</td></tr>"

    return result


def calculate_total_rows(desc, perms):
    n_rows = 1           # For the id and name row

    if desc != '':
        n_rows += 1      # For the desc, if present

    n_rows += 1          # For the instances row

    for perm in perms:
        n_rows += max(1, len(perm.get('IpRanges', [])))

    return n_rows
