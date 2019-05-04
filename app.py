from flask import Flask
from json2html import *
from customClasses import SessionHandler
from customClasses import Account
from customClasses import Organization
from customClasses import PolicyVizFacade



app = Flask(__name__)


@app.route('/')
def policy_viz():
    print ("Policy Viz")

    policyVizFacade = PolicyVizFacade()

    #RoleForFastVisualizer in account TuahaAftab
    #roleArn = 'arn:aws:iam::270192370591:role/RoleForFastVisualizer'
    #externalId = 'external_id_555'

    # User provided information
    # RoleForFastVisualizer in account SultanFarooq
    roleArn = 'arn:aws:iam::929559396084:role/RoleForFastVisualizer'
    externalId = 'external_id_555'

    # Assume role in user account
    policyVizFacade.assumeRole(roleArn, externalId)

    policyVizFacade.fetchAccountDetails()

    # Contains name of service as used by API. Eg Alexa for Business = a4b
    servicesList = policyVizFacade.fetchServicesList()

    # Services specified by user. Treemap made corresponding to each service
    #services = ['a4b', 's3', 'iam', 'ec2']
    services = ['s3']
    treemaps = policyVizFacade.buildTreemapsForServices(services)


    htmlTable = json2html.convert(json = treemaps['s3'])

    return htmlTable


if __name__ == '__main__':
    app.run()
