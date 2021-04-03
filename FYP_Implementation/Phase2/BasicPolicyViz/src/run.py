from flask import Flask, Blueprint, request, jsonify
from flask_cors import CORS
from Phase2.BasicPolicyViz.src.policy_viz import PolicyVizFacade

app = Flask(__name__)
CORS(app)

@app.route('/', methods=['GET', 'POST'])
def fetch_treemap():
    if request.args:
        role_arn = request.args.get('role_arn')
        external_id = request.args.get('external_id')
        user_specified_service_name = request.args.get('user_specified_service_name')
    else:
        role_arn = ""
        external_id = ""
        user_specified_service_name = "rds"

    policy_viz_facade = PolicyVizFacade()
    treemap = policy_viz_facade.get_policy_summary_treemap(role_arn, external_id, user_specified_service_name)

    return jsonify(treemap)

app.debug = True
app.run()
