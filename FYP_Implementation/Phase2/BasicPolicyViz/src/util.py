import csv
import re

DENIED = 0
EXPLICITLY_DENIED = -1
EXPLICITLY_ALLOWED = 1
ACCESS_LEVELS = ['List', 'Read', 'Write', 'Permissions management', 'Tagging']
SERVICES_CATEGORIZED_ACTIONS_FILE_PATH = "../resources/services_categorized_actions_files/"
GROUP_COLOUR_HEX = "#0955f6"    #Blue
USER_COLOUR_HEX = "#25b018"  #Green
OUTERMOST_BOX_COLOUR_HEX = "#0000"


def get_service_categorized_actions_status(service_name):
    """
    Reads file corresponding to service.
    The file contains possible actions along with access_level they belong to.
    The content is read into a dictionary which contains access_level as keys and corresponding actions, status as values

    :param service_name: Service name which PolicyViz user has proviced

    :return: A dictionay with contains access_level as keys.
    Actions and their status are appended as key, value pairs in the list of access_level they fall into
    """

    service_categorized_actions_status = {'*': DENIED}
    for access_level in ACCESS_LEVELS:
        service_categorized_actions_status[access_level] = {}

    file_name = SERVICES_CATEGORIZED_ACTIONS_FILE_PATH + service_name + ".csv"
    with open(file_name, 'r') as service_categorized_actions_file:
        reader = csv.reader(service_categorized_actions_file)
        for row in reader:
            action_name = row[0]
            access_level = row[1]
            status = DENIED
            service_categorized_actions_status[access_level].update({action_name: status})
    service_categorized_actions_file.close()

    return service_categorized_actions_status


def update_service_categorized_actions_status(entity, policies, specific_entity_service_categorized_actions_status, user_specified_service_name):
    """
    Parse policies attached with the entity and update specific_entity_service_categorized_actions_status accordingly

    :param entity: policies attached with this entity will be parsed. Entity is a group or a user
    :param policies: dictionary containing all fetched policies
    :param specific_entity_service_categorized_actions_status: dictionary that stores possible actions for a service and their status.
    Updated while parsing policy
    :param user_specified_service_name: policies will be summarized for the specified service only

    :return: updated specific_entity_service_categorized_actions_status
    """

    for policy_name in entity['AttachedManagedPolicies']:
        policy_document = policies[policy_name]['Document']

        for policy_statement in policy_document['Statement']:
            effect = policy_statement['Effect']
            action_list = []

            if isinstance(policy_statement['Action'], str):
                action_list.append(policy_statement['Action'])
            elif isinstance(policy_statement['Action'], list):
                action_list = policy_statement['Action']

            for action in action_list:
                action = action.split(':')
                service_name = action[0]
                if len(action) > 1:  # if action = "*", then no service_name exists
                    action_name = action[1]

                # consider only one service specified by user while parsing policy
                if service_name != user_specified_service_name:
                    continue

                # ==> ALL services - ALL actions. Example: action = "*"
                if service_name == '*' and effect == 'Deny':
                    specific_entity_service_categorized_actions_status['*'] = EXPLICITLY_DENIED
                elif service_name == '*' and effect == 'Allow':
                    if specific_entity_service_categorized_actions_status['*'] != EXPLICITLY_DENIED:
                        specific_entity_service_categorized_actions_status['*'] = EXPLICITLY_ALLOWED

                    for access_level in ACCESS_LEVELS:
                        access_level_actions_status = specific_entity_service_categorized_actions_status[access_level]
                        for action_name_stored in access_level_actions_status.keys():
                            if access_level_actions_status[action_name_stored] != EXPLICITLY_DENIED:
                                access_level_actions_status[action_name_stored] = EXPLICITLY_ALLOWED

                # ==> ONE service - ALL actions. Example: action = "rds:*"
                elif action_name == '*' and effect == 'Deny':
                    specific_entity_service_categorized_actions_status['*'] = EXPLICITLY_DENIED
                elif action_name == '*' and effect == 'Allow':
                    if specific_entity_service_categorized_actions_status['*'] != EXPLICITLY_DENIED:
                        specific_entity_service_categorized_actions_status['*'] = EXPLICITLY_ALLOWED

                    for access_level in ACCESS_LEVELS:
                        access_level_actions_status = specific_entity_service_categorized_actions_status[access_level]
                        for action_name_stored in access_level_actions_status.keys():
                            if access_level_actions_status[action_name_stored] != EXPLICITLY_DENIED:
                                access_level_actions_status[action_name_stored] = EXPLICITLY_ALLOWED

                # ==> ONE service - MULTIPLE actions. Example: action = "rds:Describe*"
                elif '*' in action_name and effect == 'Deny':
                    for access_level in ACCESS_LEVELS:
                        access_level_actions_status = specific_entity_service_categorized_actions_status[access_level]
                        for action_name_stored in access_level_actions_status.keys():
                            action_name_regex = action_name.replace('*', '.*')
                            if re.match(action_name_regex, action_name_stored):
                                access_level_actions_status[action_name_stored] = EXPLICITLY_DENIED
                elif '*' in action_name and effect == 'Allow':
                    for access_level in ACCESS_LEVELS:
                        access_level_actions_status = specific_entity_service_categorized_actions_status[access_level]
                        for action_name_stored in access_level_actions_status.keys():
                            action_name_regex = action_name.replace('*', '.*')
                            if re.match(action_name_regex, action_name_stored):
                                if access_level_actions_status[action_name_stored] != EXPLICITLY_DENIED:
                                    access_level_actions_status[action_name_stored] = EXPLICITLY_ALLOWED

                # ==> ONE service - ONE action. Example: action = "rds:StartDBInstance"
                elif '*' not in action_name and effect == 'Deny':
                    for access_level in ACCESS_LEVELS:
                        access_level_actions_status = specific_entity_service_categorized_actions_status[access_level]
                        if action_name in access_level_actions_status:
                            access_level_actions_status[action_name] = EXPLICITLY_DENIED
                elif '*' not in action_name and effect == 'Allow':
                    for access_level in ACCESS_LEVELS:
                        access_level_actions_status = specific_entity_service_categorized_actions_status[access_level]
                        if action_name in access_level_actions_status:
                            if access_level_actions_status[action_name] != EXPLICITLY_DENIED:
                                access_level_actions_status[action_name] = EXPLICITLY_ALLOWED

def summarize_policies(service_categorized_actions_status):
    """
    Parses service_categorized_actions_status and makes a summary based on it.

    :param service_categorized_actions_status: dictionary that stores possible actions for a service and their status.
    Updated while parsing policy

    :return: a summary of the policies made by parsing service_categorized_actions_status
    """

    policies_summary = {'FullAccess': False, 'Full': set(), 'Limited': set()}

    if service_categorized_actions_status['*'] == -1:  # all explicitly denied
        return policies_summary

    for access_level in ACCESS_LEVELS:
        actions_status_in_access_level = service_categorized_actions_status[access_level]

        count_actions = {"denied": 0, "explicitly_denied": 0, "explicitly_allowed": 0}
        for action_name, action_status in actions_status_in_access_level.items():
            if action_status == EXPLICITLY_DENIED:
                count_actions["explicitly_denied"] += 1
            elif action_status == DENIED:
                count_actions["denied"] += 1
            elif action_status == EXPLICITLY_ALLOWED:
                count_actions["explicitly_allowed"] += 1

        all_actions_allowed = True
        total_actions_in_access_level = len(actions_status_in_access_level)
        if count_actions["explicitly_allowed"] == total_actions_in_access_level:  # All actions are allowed
            policies_summary['Full'].add(access_level[0])  # First letter of access level is appended
        elif count_actions["explicitly_allowed"] > 0:  # Some actions are allowed
            policies_summary['Limited'].add(access_level[0])
            all_actions_allowed = False
        else:
            all_actions_allowed = False

    policies_summary['Full'] = sorted(policies_summary['Full'])
    policies_summary['Limited'] = sorted(policies_summary['Limited'])
    policies_summary['FullAccess'] = all_actions_allowed

    return policies_summary


def build_tree_map_from_summaries(groups, users, groups_summaries, users_summaries, user_specified_service_name):
    """
    This function form a treemap from the summarized policies of groups and users
    :param groups: information about AWS groups
    :param users: information about AWS users
    :param groups_summaries: contains summarized managed policies for each group
    :param users_summaries: contains summarized managed policies for each user
    :return: treemap
    """

    # Creating treemap with outermost box
    treemap = dict()
    groups_to_add_in_treemap = dict()
    users_to_add_in_treemap = dict()

    # Adding groups to groups_to_add_in_treemap
    for group_name, group_summary in groups_summaries.items():
        child = {'hex':GROUP_COLOUR_HEX, 'value': 3000}
        child['title'] = "(" + group_name + ") " + str(group_summary)
        child['children'] = []
        groups_to_add_in_treemap[group_name] = child

    # Adding users to users_to_add_in_treemap
    for user_name, user_summary in users_summaries.items():
        child = {'hex':USER_COLOUR_HEX, 'value': 3000}
        child['title'] = "(" + user_name + ") " + str(user_summary)
        users_to_add_in_treemap[user_name] = child

    # Adding users as children of groups they belong to
    for user_name, user in users.items():
        for group_name in user['GroupList']:
            if groups_to_add_in_treemap.get(group_name):
                child_user = users_to_add_in_treemap[user_name]
                groups_to_add_in_treemap[group_name]['children'].append(child_user)

    # Setting up outer most box
    treemap['title'] = "IAM Summarized Policies for service: " + user_specified_service_name
    treemap['hex'] = OUTERMOST_BOX_COLOUR_HEX
    treemap['value'] = 5000
    treemap['children'] = []

    # Setting up box for groups
    group_treemap = {'title': 'GROUPS', 'hex':OUTERMOST_BOX_COLOUR_HEX, 'value': 5000}
    group_treemap['children'] = ([child for child in groups_to_add_in_treemap.values()])

    # Setting up box for users
    user_treemap = {'title': 'USERS', 'hex': OUTERMOST_BOX_COLOUR_HEX, 'value': 5000}
    user_treemap['children'] = ([child for child in users_to_add_in_treemap.values()])

    treemap['children'].append(group_treemap)
    treemap['children'].append(user_treemap)

    return treemap
