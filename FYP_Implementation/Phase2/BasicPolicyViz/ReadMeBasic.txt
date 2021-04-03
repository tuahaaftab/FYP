Setup Environment:
    Setup virtual environment (venv)
    Install boto3 (pip install boto3)


Code:
    Policies for groups and users are summarized.
    Only managed policies are summarized. Inline policies are not included currently.
    If multiple versions of a policy exist, the default version is chosen.

    Elements of a policy that are parsed for creating summary:
        -> Effect
        -> Actions
            -> actions with wildcard '*' that replaces action name are handled. Example: rds:Describe*

    While summarizing policies, only those actions for a service are considered that are present in its categorized_actions_file.
    The categorized_actions_file for a service is present in resources->services_categorized_actions_files.
    These files are made by referencing:
        -> https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_actions-resources-contextkeys.html


Index:
    PolicyViz account: The application creates an initial session with this AWS account
    PolicyViz user: The person using the PolicyViz application
	
Visualization:
	The JSON fetched from invoking the fetch_treemap() REST API can be visualized using React JS TreeMap API