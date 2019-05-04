import boto3
import queue
import os
import csv
import json
import numpy as np
from collections import defaultdict

class PolicyVizFacade:
    def __init__(self):
        self.sessionHandler = SessionHandler()
        self.treemapBuilder = TreemapBuilder()

    def assumeRole(self, roleArn, externalId):
        # todo : exception handling
        self.sessionHandler.assumeRole(roleArn, externalId)

    def fetchAccountDetails(self):
        self.sessionHandler.fetchAccountDetails()

    def fetchServicesList(self):
        fname = "./resources/services.txt"

        services = {}

        if os.path.exists(fname):
            with open(fname, 'r') as servicesFile:
                reader = csv.reader(servicesFile)
                for row in reader:
                    services[row[0]] = row[1].strip()

            servicesFile.close()

            return services
        else:
            print("Error while reading services file")
            return None

    # Build treemap for each service and return all treemaps in array
    def buildTreemapsForServices(self, services):
        # Retrive from stored files
        self.treemapBuilder.retrieveActionsSummaryTables(services)
        #Checking for only one service
        organization = self.sessionHandler.getOrganization()
        treemaps = self.treemapBuilder.buildTreemapsForServices(services, organization)

        return treemaps



class TreemapBuilder:
    def __init__(self):
        #Contain treemap against each service. ec2 = trremap for ec2
        self.servicesTreemaps = {}
        self.servicesTreemaps2 = {}
        self.actionsSummaryTables = {}

    def printTreemap(self, treemap):
        pass

    def buildTreemapsForServices(self, services, organization): #buildTreemapForOrganizationSCPs
        for service in services:
            self.servicesTreemaps[service] = []

        ou = organization.getOrganizationRoot()
        self.q = queue.LifoQueue(maxsize=0)
        self.q.put(ou)

        self.evaluateOrganizationTree(services)

        # todo : treemaps
        jsonTreemaps = {}
        for service in services:
            treemap = json.dumps(self.servicesTreemaps2[service], indent=4)
            jsonTreemaps[service] = treemap
            print ("treemap", service, treemap)

        return jsonTreemaps

    # servicesStatus2[service] == {'FullAccess': False, 'Full':(a4b), 'Limited'=(s3, ec2) ] Full and limited are sets
    def buildTreemapForService(self, service, servicesStatus, totalPath, ouName, ouParentName):

        '''for nodeName in totalPath:      #adding dictionary within dictionary to build a json for treemap
            dictionary[nodeName] = {}
            dictionary = dictionary[nodeName]'''


        #Adding node of treemap
        node = {}
        node['label'] = ouName
        node['value'] = 0
        if ouParentName != '':
            node['parent'] = ouParentName

        if (servicesStatus[service] == -1):
            node['colour'] = "RED"
        elif (servicesStatus[service] == 0):
            node['colour'] = "ORANGE"
        elif (servicesStatus[service] == 1):
            node['colour'] = "GREEN"
        else:
            node['colour'] = "White"

        self.servicesTreemaps[service].append(node)
        #print("node", node)

    def buildTreemapForService2(self, service, servicesStatus, totalPath, ouName, ouParentName, ouIsLeaf):

        '''for nodeName in totalPath:      #adding dictionary within dictionary to build a json for treemap
            dictionary[nodeName] = {}
            dictionary = dictionary[nodeName]'''

        servicesTreemaps2 = self.servicesTreemaps2

        '''
        print("Organizational Unit\t\t:", ouName)
        print("Organizational Unit Parent Name\t\t:", ouParentName)
        print("Organizational Unit Parent Path\t\t:", totalPath)
        for service in servicesStatus.keys():
            print ('\t', service)
            print ('\t', servicesStatus[service])
            servicesTreemaps2[service] = {}
        '''

        #self.servicesTreemaps2[service]

        elements = []  # contains children array of elements

        # Adding first element in treemap
        if ouName == "Root":
            servicesTreemaps2[service] = {}
            servicesTreemaps2[service]['title'] = ouName
            servicesTreemaps2[service]['color'] = servicesStatus[service]['Color']
            #info should contain information about the access. Full = L, R.  Limited = W
            info = 'FullAccess=' + str(servicesStatus[service]['FullAccess'])

            temp = ''
            for accessLevel in servicesStatus[service]['Full']:
                temp += accessLevel + '-'
            if len(servicesStatus[service]['Full']) > 0:
                info += ', Full=' + temp[:-1]

            temp = ''
            for accessLevel in servicesStatus[service]['Limited']:
                info += accessLevel + '-'
            if len(servicesStatus[service]['Limited']) > 0:
                info += ', Limited=' + temp[:-1]

            #servicesTreemaps2[service]['info'] = info
            servicesTreemaps2[service]['title'] += ' -> ' + info
            servicesTreemaps2[service]['children'] = []


            if ouIsLeaf:
                servicesTreemaps2[service]['size'] = 1000
            else:
                servicesTreemaps2[service]['children'] = []
        else:

            elements = [] #contains children array of elements
            ancestorPath = totalPath[:-1] #Ignoring last element which is current ou name
            for ancestor in ancestorPath:
                if ancestor == 'Root':
                    elements = servicesTreemaps2[service]['children']  # Children of root
                else:
                    ancestorFound = False
                    elementIndex = 0
                    lenElements = len(elements)
                    while (elementIndex < lenElements) and (not ancestorFound):
                        if elements[elementIndex]['title'] == ancestor:
                            elements = elements[elementIndex]['children']
                            ancestorFound = True

                        elementIndex += 1

            # Inside parent children

            newElement = {}
            newElement['title'] = ouName
            newElement['color'] = servicesStatus[service]['Color']
            #newElement['info'] = servicesStatus[service]['Limited']['Full'] etc
            #servicesTreemaps2[service]['info'] = servicesStatus[service]
            info = 'FullAccess=' + str(servicesStatus[service]['FullAccess'])


            temp = ''
            for accessLevel in servicesStatus[service]['Full']:
                temp += accessLevel + '-'
            if len(servicesStatus[service]['Full']) > 0:
                info += ', Full=' + temp[:-1]


            temp = ''
            for accessLevel in servicesStatus[service]['Limited']:
                temp += accessLevel + '-'

            if len(servicesStatus[service]['Limited']) > 0:
                info += ', Limited=' + temp[:-1]

            #newElement['info'] = info
            newElement['title'] += ' -> ' + info

            if ouIsLeaf:
                newElement['size'] = 1000
            else:
                newElement['children'] = []


            elements.append(newElement)

        self.servicesTreemaps2 = servicesTreemaps2

        '''
        #Adding node of treemap
        node = {}
        node['label'] = ouName
        node['value'] = 0
        if ouParentName != '':
            node['parent'] = ouParentName

        if (servicesStatus[service] == -1):
            node['colour'] = "RED"
        elif (servicesStatus[service] == 0):
            node['colour'] = "ORANGE"
        elif (servicesStatus[service] == 1):
            node['colour'] = "GREEN"
        else:
            node['colour'] = "White"

        self.servicesTreemaps[service].append(node)
        #print("node", node)
        '''

    def evaluateOrganizationTree(self, services):   #Parses whole tree
        if (self.q.empty()):
            return


        ou = self.q.get()
        #print (ou.getName(), " parent path: ", ou.getParentPath())


        # check services authorization situation at OU
        servicesStatus = ou.checkIfServicesAllowed(services, self.actionsSummaryTables)
        #todo: use below
        #servicesStatus2[service] == {'FullAccess': False, 'Limited'=(s3, ec2) }
        #todo : rename serviceStatusAtOU
        servicesStatus2 = ou.checkIfServicesAllowed2(services, self.actionsSummaryTables)

        ouName = ou.getName()
        ouParentName = ou.getParentName()
        ouParentPath = ou.getParentPath()
        if ouParentPath == '':
            totalPath = []
        else:
            totalPath = (ouParentPath).split(',')

        #if ouName != '':
        totalPath.append(ouName)

        #if len(ou.children) == 0:
        #    ou.setAsLeaf()

        ouIsLeaf = ou.isLeaf()
        # Passing each OU one by one
        for service in services:
            #self.buildTreemapForService(service, servicesStatus, totalPath, ouName, ouParentName)
            self.buildTreemapForService2(service, servicesStatus2, totalPath, ouName, ouParentName, ouIsLeaf)

        for child in ou.children:
            self.q.put(child)




        self.evaluateOrganizationTree(services)

    # Reading from csv files of service and updating summaryTable
    def fillActionSummaryTable(self, serviceName):

        fname = "./tempResources/" + serviceName + ".csv"

        services = {}

        if os.path.exists(fname):
            with open(fname, 'r') as summaryFile:
                reader = csv.reader(summaryFile)
                #row[1] contains access level and row[0] specifies the action
                # Todo: skip first line.
                for row in reader:
                    self.actionsSummaryTables[serviceName][row[1]].append(row[0])

            summaryFile.close()


            return services
        else:
            print("Error while reading summary table file of service: " + serviceName)
            return None

    # Retrieve action summary tables
    # https: // docs.aws.amazon.com / IAM / latest / UserGuide / reference_policies_actions - resources - contextkeys.html
    # Action summary table of all services
    # The actions are grouped as List, Read, Write, Permissions management, Tagging
    def retrieveActionsSummaryTables(self, services):
        self.actionsSummaryTables = {}

        accessLevels = ['List', 'Read', 'Write', 'Permissions management', 'Tagging']

        # Todo: add files of summary table for all services
        for service in services:
            self.actionsSummaryTables[service] = {}
            for accessLevel in accessLevels:
                self.actionsSummaryTables[service][accessLevel] = []


        for service in services:
            self.fillActionSummaryTable(service)
            #print("Service Table:", service)
            #print (self.actionsSummaryTables[service])

    def getActionsSummaryTable(self):
        return self.actionsSummaryTables

class SessionHandler:
    def __init__(self):

        #SultanAdmin credentials
        '''
        self.mainSession = boto3.session.Session(
            aws_access_key_id="AKIAJ7DHLQEOZC6GYZQQ",
            aws_secret_access_key="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"
        )
        '''

        # TuahaAdmin credentials

        self.mainSession = boto3.session.Session(
            aws_access_key_id="AKIAT52FYMOPUC4CF22J",
            aws_secret_access_key="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"
        )


    def getOrganization(self):
        return self.account.getAssociatedOrganization()

    def assumeRole(self, roleArn, externalId):
        #roleCredentials will contains role access keys
        roleCredentials = self.getRoleCredentials(roleArn, externalId)

        #a session with aws will be established using roleCredentials
        self.session = self.createSession(roleCredentials)

    def getRoleCredentials(self, roleArn, externalId):
        stsClient = self.mainSession.client('sts')
        #RoleForFastVisualizer in SultanFarooq
        assumedRole = stsClient.assume_role(
            RoleArn=roleArn,
            RoleSessionName='session5',
            DurationSeconds=900,
            ExternalId=externalId
        )
        # config= "us-west-1"

        return assumedRole

    def createSession(self, roleCredentials):
        session = boto3.session.Session(
            aws_access_key_id=roleCredentials['Credentials']['AccessKeyId'],
            aws_secret_access_key=roleCredentials['Credentials']['SecretAccessKey'],
            aws_session_token=roleCredentials['Credentials']['SessionToken']
        )

        return session

    def fetchAccountDetails(self):
        self.account = Account(self.session) #Initialize account with internal account details
        self.account.setAsOrganiztionHead() #Set first account as organization head
        self.account.confirmAsOrganizationHead(self.session) #check if account actually root of organization
        self.account.initializeOrganization(self.session) #Initalize organization if root


    def fetchUsersDetails():
        print("fetchUsersDetails")

    def fetchRolesDetails():
        print("fetchRolesDetails")

    def fetchGroupsDetails():
        print("fetchGroupsDetails")

    def fetchOrganizationDetails():
        print("fetchOrganizationDetails")

    def fetchServicesDetails():
        print("fetchAccountDetails")

    def visualizeAuthorizationPolicies(self):
        print ("visualizeAuthorizationPolicies")




class Account:
    def __init__(self, session):
        iamClient = session.client('iam')

        self.arn = ''
        self.name = ''

        users = iamClient.list_users()
        self.setUsers(users, session)  #Can also pass IAM client here

        groups= iamClient.list_groups()
        self.setGroups(groups, session)

        self.isOrganizationHead = False   #Every account is not a root account

        self.checkIfOrganizationExists(session)


    def checkIfOrganizationExists(self, session):
        organizationClient = session.client('organizations')

        try:
            #Below function can only be called if account part of organization
            organizationInfo = organizationClient.describe_organization()
            self.isPartOfOrganization = True
            self.organizationInfo = organizationInfo
            #print ("Account part of organization")

        except Exception as e:
            print ("Account not part of organization or account does not have permission to view organization details")
            return


    def confirmAsOrganizationHead(self, session):
        organizationClient = session.client('organizations')

        try:
            # Below function can only be called if account root of organization
            organizationRoots = organizationClient.list_roots()
            #print("Account head of organization")
        except Exception as e:
            print("Account not root of organizations")
            self.isOrganizationHead = False
            return

    def setAsOrganiztionHead(self):
        self.isOrganizationHead = True


    def initializeOrganization(self, session):
        if not self.isOrganizationHead:
            return

        organizationClient = session.client('organizations')

        organizationInfo = organizationClient.describe_organization()

        self.organization = Organization(session)

    def getAssociatedOrganization(self):     #setOrganization no need
        return self.organization



    def setUsers(self, users, session):
        #print ("\n\nAccount Users\n", users)
        pass

    def setGroups(self, groups, session):
        #print ("\n\nAccount Groups\n",groups)
        pass

    def setRoles(self):
        print ("roles")

    def getUsers(self):
        print ("\n\nAccount Users\n")

    def getGroups(self):
        print ("\n\nAccount Groups\n")

    def getRoles(self):
        print("roles")

    def setArn(self, arn):
        self.arn = arn

    def setName(self, name):
        self.name = name

    def getArn(self):
        return self.arn

    def getName(self, name):
        return self.name

    def getRoot(self):
        return self.root

class Organization:
    def __init__(self, session):
        self.arn = ''
        self.name = ''
        self.root = ''

        organizationClient = session.client('organizations')

        response = organizationClient.describe_organization()
        self.organization_info = response['Organization'] #Ignoring metadata information in response

        #todo: use supportPolicies
        # todo: if supportPolicies = True, check if SCP enabled
        self.supportsPolicies = False
        if self.organization_info['FeatureSet'] == 'ALL':   #The organization support attaching SCPs else only consolidated billinh
            self.supportsPolicies = True

        #print ("Organization Supports Policies: ", self.supportsPolicies)


        #print("\n\nOrganization Info\n", organization_info)

        self.accounts = organizationClient.list_accounts()
        #print("\n\nOrganization accounts\n", accounts)

        self.organizationRoots = organizationClient.list_roots()
        #print("\n\nOrganization Roots\n", organizationRoots)

        self.setOrganizationRoot(self.organizationRoots)

        # Initializing queue with rootNode
        # Queue used for BFS traversal
        self.queue = queue.Queue(maxsize=0)
        self.queue.put(self.root)



        self.buildOrganization(organizationClient)


    def setOrganizationRoot(self, organizationRoots):
        self.root = RootOrganizationalUnit(organizationRoots['Roots'][0])

    def getOrganizationRoot(self):
        return self.root


    def buildOrganization(self, organizationClient):
        #print ("buildOrganization")

        #Using bfs to build organization tree
        if (self.queue.empty()):
            return

        ou = self.queue.get()
        ou.fetchDetails(organizationClient) #fetch details related to accounts, policies

        totalPath = '' #Represents path till current node
        if ou.isRoot:
            totalPath = ou.getName()
        else:
            totalPath = ou.getParentPath() + "," + ou.getName()

        childOUs = organizationClient.list_organizational_units_for_parent(
            ParentId=ou.id
        )

        ou.addChildren(childOUs, ou.level + 1, totalPath)  #Adding nodes with information about OUs at level in tree greater than previous

        if len(ou.children) == 0:
            ou.setAsLeaf()

        for child in ou.children:  #A child is an organizational unit
            self.queue.put(child)

        self.buildOrganization(organizationClient)



    def setArn(self, arn):
        self.arn = arn

    def setName(self, name):
        self.name = name

    def getArn(self):
        return self.arn

    def getName(self, name):
        return self.name


class OrganizationalUnit:
    def __init__(self, data):
        self.id = data['Id']
        self.arn = data['Arn']
        self.name = data['Name']
        self.parentName = ""

        self.children = []      #List of organizational units
        self.level = 0

        self.policies = []

        self.parentPath = ''
        self.isRoot = False

        self.serviceAuthorizationSituation = {}
        self.organizationalUnitSummary = {}     # Use this instead of serviceAuthorizationSituation
        self.ouPoliciesEvaluated = False    #True if policies at OU evaluated

        self.nodeIsLeaf = False

    def addChildren(self, childOUs, level, parentPath):

        for ou in childOUs['OrganizationalUnits']:
            childOU = OrganizationalUnit(ou)    #Setting node data
            childOU.level = level
            childOU.setParentPath(parentPath)   #totalPath = ou.getParentPath() + "," + ou.getName()
            childOU.setParentName(self.name)

            self.children.append(childOU)


    def setParentName(self, parentName):
        self.parentName = parentName

    def getParentName(self):
        return self.parentName

    def setParentPath(self, parentPath):
        self.parentPath = parentPath

    def getParentPath(self):
        return self.parentPath

    def setAsLeaf(self):
        self.nodeIsLeaf = True

    def isLeaf(self):
        return self.nodeIsLeaf

    # checkIfServicesAllowed : checks the status of services specified by using policies attached with an Organizational Unit
    # input   : a list of services
    # returns : dictionary ec2:1, s3:0 that tell status of services
    def checkIfServicesAllowed(self, userSpecifiedServices, actionsSummaryTable):
        if not self.ouPoliciesEvaluated:
            self.evaluateOuPolicies(userSpecifiedServices, actionsSummaryTable)

        servicesStatus = {} #service status at this OU eg ec2=1, s3=0
        for service in userSpecifiedServices:
            servicesStatus[service] = self.checkIfServiceAllowed(service)

        #print ("servicesStatus", servicesStatus)
        return servicesStatus

    # checkIfServiceAllowed : checks the status of a service in policies attached with an Organizational Unit
    # input   : a service name string
    # returns : -1(denied), 0(denied implicity), 1(allowed explicitly)
    def checkIfServiceAllowed(self, service):
        #Checking for explicit deny
        if self.serviceAuthorizationSituation['*'] == -1: #all services denied explicitly
            return -1;

        # Checking for explicit deny first then for explicit allow
        if service in self.serviceAuthorizationSituation: #service was explicitly mentioned in policy
            if self.serviceAuthorizationSituation[service] == -1: #denied explicitly
                return -1
            elif self.serviceAuthorizationSituation[service] == 1: #allowed explicitly
                return 1
            #self.serviceAuthorizationSituation[service] == 0, then check if allowed by '*'

        if self.serviceAuthorizationSituation['*'] == 1: #all allowed explicitly
            return 1

        if self.serviceAuthorizationSituation['*'] == 0: #all denied implicitly
            return 0

    # checks the status of services specified by using policies attached with an Organizational Unit
    # input   : a list of services
    # returns : dictionary ec2:{Color=white, FullAccess=True, 'Write'='FULL'}
    # s3:{Color=white, FullAccess=False, 'Write'='Limited'}
    def checkIfServicesAllowed2(self, userSpecifiedServices, actionsSummaryTable):
        if not self.ouPoliciesEvaluated:
            self.evaluateOuPolicies(userSpecifiedServices, actionsSummaryTable)

        # service status at this OU.
        # serviceStatus[service] = {Color=white, FullAccess=True, 'Write'='Limited', 'Read'='Full', 'List'='None'}
        servicesStatus = {}
        for service in userSpecifiedServices:
            servicesStatus[service] = self.checkIfServiceAllowed2(service)

        #print ("servicesStatus", servicesStatus)
        return servicesStatus

    # checkIfServiceAllowed : checks the status of a service in policies attached with an Organizational Unit
    # input   : a service name string
    # returns : {Color=white, FullAccess=False, Limited: List, Read, 	Full: List}
    def checkIfServiceAllowed2(self, service):
        # summary {Color=white, FullAccess=False, Limited: List, Read, 	Full: List
        # If no access. 'Color'='Red' Implicitly denied. 'Color'='Red' Explicitly denied.
        summary = {'FullAccess':False, 'Full':set(), 'Limited':set(), 'Color':'Red'}

        if self.organizationalUnitSummary[service]['*'] == -1: # all explicitly denied
            summary['Color'] = 'Red'
            return summary

        # tempResults is a matrix that stores the number of -1, 0, 1 encountered
        # in accessLevel array states.
        # Loop over accessLevel information states and fill summary info accordingly

        accessLevels = ['List', 'Read', 'Write', 'Permissions management', 'Tagging']

        allActionsForServiceAllowed = True
        for accessLevel in accessLevels:
            actionsStateInAccessLevel = self.organizationalUnitSummary[service][accessLevel]

            totalActionsInAccessLevel = len(self.organizationalUnitSummary[service][accessLevel])
            statesCount = np.zeros((3,), dtype=int) #corresponding to -1, 0, 1
            for state in actionsStateInAccessLevel:
                if state == -1:         #action explicitly denied
                    statesCount[0] += 1
                elif state == 0:        #action implicitly denied
                    statesCount[1] += 1
                elif state == 1:        #action explicitly allowed
                    statesCount[2] += 1

            # All actions for access level are allowed
            if statesCount[2] == totalActionsInAccessLevel: # All actions are allowed
                summary['Full'].add(accessLevel[0])
            elif statesCount[2] > totalActionsInAccessLevel: # Some actions are allowed
                summary['Limited'].add(accessLevel[0])
                allActionsForServiceAllowed = False
            else:
                allActionsForServiceAllowed = False

        summary['FullAccess'] = allActionsForServiceAllowed

        # colour only based upon if read and write present in lists
        color = ""
        readAllowed = False
        writeAllowed = False

        if ('R' in summary['Full']) or ('R' in summary['Limited']):
            readAllowed = True
        if ('W' in summary['Full']) or ('W' in summary['Limited']):
            writeAllowed = True

        if readAllowed and writeAllowed:
            summary['Color'] = "Green"
        elif readAllowed :
            summary['Color'] = "Yellow"
        elif writeAllowed:
            summary['Color'] = "Blue"
        elif (not readAllowed) and (not writeAllowed):
            summary['Color'] = "Red"

        return summary

        # organizationalUnitSummary[service][accessLevel] = [0, 0, 0, 0, 1, -1, 1, 0, 0]
        '''
        if self.serviceAuthorizationSituation['*'] == -1: #all services denied explicitly
            return -1;

        # Checking for explicit deny first then for explicit allow
        if service in self.serviceAuthorizationSituation: #service was explicitly mentioned in policy
            if self.serviceAuthorizationSituation[service] == -1: #denied explicitly
                return -1
            elif self.serviceAuthorizationSituation[service] == 1: #allowed explicitly
                return 1
            #self.serviceAuthorizationSituation[service] == 0, then check if allowed by '*'

        if self.serviceAuthorizationSituation['*'] == 1: #all allowed explicitly
            return 1

        if self.serviceAuthorizationSituation['*'] == 0: #all denied implicitly
            return 0
        '''

    # evaluateOuPolicies : Evaluate all policies attached with an Organizational Unit
    # input  : none
    # output : totalServiceAuthorizationSituation contains result after evaluating policies
    # Checks if user selected services are allowed, denied, or explicitly denied at this OU
    def evaluateOuPolicies(self, userSpecifiedServices, actionsSummaryTable):
        # Todo : actionsSummaryTable in Treemap builder should contain information for all policies and execute once
        # Todo : Include wildcard checks differently in iam policy checker
        # In an SCP, the wildcard (*) character in an Action or NotAction element can be used only by itself or at the end of the string. It can't appear at the beginning or middle of the string. Therefore, "servicename:action*" is valid, but "servicename:*action" and "servicename:some*action" are both invalid in SCPs.

        totalServiceAuthorizationSituation = {}  #Dictionary contains service:status as pairs for all services mentioned in policies
        totalServiceAuthorizationSituation['*'] = 0 #All denied implicitly initially

        # will store summary of permissions of OU. Will contain mapping against actionsSummaryTable
        # First rank will contain services
        # Second rank will contain access level keys
        # Third rank will contain an array of ints. Each index of array will correspond to
        # a particular action in actionsSummaryTable[service][accessLevel]
        organizationalUnitSummary = {}
        accessLevels = ['List', 'Read', 'Write', 'Permissions management', 'Tagging']

        # Initializing organizationalUnitSummary
        for service in userSpecifiedServices:
            organizationalUnitSummary[service] = {}
            organizationalUnitSummary[service]['*'] = 0  # For all possible actions against service
            for accessLevel in accessLevels:
                # number of actions in accessLevel

                lenAccessLevelActions = len(actionsSummaryTable[service][accessLevel])
                # organizationalUnitSummary[service][accessLevel] will containg number corresponding to if service allowed
                # actionsSummaryTable['s3']['Read'] =        ['GetObject', 'ListObjects, ... ]
                # organizationalUnitSummary['s3']['Write'] = [ 0, 0]  Initially implicitly denied

                organizationalUnitSummary[service][accessLevel] = np.zeros((lenAccessLevelActions,), dtype=int)




        for policy in self.policies:    #Each policy is a ServiceControlPolicy. Policies are fetched in fetchPolicies
            policyStatements = policy.getPolicyStatements() #Each policy statement contains effect, action, resources

            for policyStatement in policyStatements:
                # Only considering if a service is denied explicitly, denied implicitly, or allowed at this level
                # Therefore no need for particular actions and resources
                effect = policyStatement['Effect']
                resources = policyStatement['Resource']  #list of resources, not used currently

                actions = []
                # actions should be a list containg action. If only single action not in list,
                # then make and append to list for consistency in loops.
                if isinstance(policyStatement['Action'], str):
                    actions.append(policyStatement['Action'])
                else:
                    actions = policyStatement['Action']

                listedServices = [] #listed services in policy eg ec2:read , ec2 is a listedService
                allServicesSelected = False #This is set to true if action contains '*' instead of a specific service



                for a in actions:
                    #todo : take out service from all types of actions
                    action = a.split(':') #ec2:read
                    service = action[0]
                    if action[0] == '*':
                        allServicesSelected = True  #action contains '*' to specify all actions with all services


                        # All actions of all services
                        if effect == 'Deny':
                            for service in organizationalUnitSummary.keys():
                                organizationalUnitSummary[service]['*'] = -1

                        elif effect == 'Allow':
                            for service in organizationalUnitSummary.keys():
                                if organizationalUnitSummary[service]['*'] != -1:
                                    organizationalUnitSummary[service]['*'] = 1

                                for accessLevel in accessLevels:
                                    actionsStateInAccessLevel = organizationalUnitSummary[service][accessLevel]
                                    actionsStateInAccessLevel[actionsStateInAccessLevel == 0] = 1

                        continue #Skip rest of loop

                    # ================previous=================
                    if service not in listedServices:   #collection of services listed in a policyStatement
                        listedServices.append(action[0])
                        # initializaing array with denied implicitly. This array will contain infromation regarding all services mentioned in policies
                        # also including those services not required by user
                        totalServiceAuthorizationSituation[service] = 0

                    # ================previous=================

                    # todo : Keep condition but make files for all available services
                    # actionsSummaryTable does not contain action summary for services
                    # whose csv file not available in resources
                    serviceDetailsAvailable = True
                    if action[0] not in actionsSummaryTable.keys():
                        # action[0] contains service name
                        print("CSV file not available for service: ", action[0])
                        serviceDetailsAvailable = False


                    # if action is a particular action like s3:ListObjects. ListObjects is a particular action.
                    if '*' not in action[1] and (serviceDetailsAvailable):
                        # below in for actionsSummaryTable
                        for accessLevel in accessLevels:
                            # If specified action not recorded in access level for service
                            if action[1] not in actionsSummaryTable[service][accessLevel]:
                                continue

                            # index of particular action in actionsSummaryTable[service][accessLevel]:
                            index = actionsSummaryTable[service][accessLevel].index(action[1])
                            if effect == 'Deny':
                                organizationalUnitSummary[service][accessLevel][index] = -1
                            elif effect == 'Allow':
                                if organizationalUnitSummary[service][accessLevel][index] != -1:
                                    organizationalUnitSummary[service][accessLevel][index] = 1

                    # if action is a all actions like s3:*. * represents all actions for service
                    elif action[1] == '*' and (serviceDetailsAvailable):
                        # below in for actionsSummaryTable
                        for accessLevel in accessLevels:
                            # Traversing array which contains number corresponding to particular actions
                            # ParticularActionState is an int in array. It represents if corresponding
                            # action in actionsSummaryTable[service][accessLevel] is allowed, denied
                            for index, particularActionState in enumerate(organizationalUnitSummary[service][accessLevel]):
                                if effect == 'Deny':
                                    organizationalUnitSummary[service][accessLevel][index] = -1
                                elif effect == 'Allow':
                                    if particularActionState != -1:
                                        organizationalUnitSummary[service][accessLevel][index] = 1

                    # if action is a all actions like s3:List*. Lisr* represents all actions with prefix List
                    # In SCP * can only come in end
                    elif '*' in action[1] and (serviceDetailsAvailable):
                        # todo : wildcards can be more flexible in iam policies
                        # wild card should only come at end
                        if action[1][-1] == '*':
                            prefix = action[1][:-1]

                            for accessLevel in accessLevels:
                                # Traversing array which contains state corresponding to particular actions
                                #print(actionsSummaryTable[service][accessLevel])
                                for index in range(len(actionsSummaryTable[service][accessLevel])):
                                    particularAction = actionsSummaryTable[service][accessLevel][index]
                                    # prefix should match first half. Eg s3:List*. List == ListObjects
                                    if (prefix in particularAction) and (prefix == particularAction[ :len(prefix)]):
                                        if effect == 'Deny':
                                            organizationalUnitSummary[service][accessLevel][index] = -1
                                        elif effect == 'Allow':
                                            if organizationalUnitSummary[service][accessLevel][index] != -1:
                                                organizationalUnitSummary[service][accessLevel][index] = 1


            #=====================previous================================================

                if allServicesSelected: #All listed services are changed

                    if effect == 'Deny':    #All listed services are changed to
                        #serviceAuthorizationSituation['*'] = -1  # All services denied explicity
                        totalServiceAuthorizationSituation['*'] = -1  # All services denied explicitly

                    elif effect == 'Allow':
                        if totalServiceAuthorizationSituation['*'] == 0:
                            totalServiceAuthorizationSituation['*'] = 1  # All services allowed explicity

                elif effect == 'Deny': #Specifically listed services in policy are denied
                    for service in listedServices:  #For all listed services in policy actions
                        totalServiceAuthorizationSituation[service] = -1 # catering all mentioned services

                elif effect == 'Allow': #Specifically listed services in policy are allowed if before denied explicitly
                    for service in listedServices:

                        #if service in totalServiceAuthorizationSituation:
                        if totalServiceAuthorizationSituation[service] == 0:  # denied implicitly
                            totalServiceAuthorizationSituation[service] = 1  # allow explicitly

            # =====================previous================================================

        self.ouPoliciesEvaluated = True
        #print ("total service authorization situations: ", totalServiceAuthorizationSituation)
        self.serviceAuthorizationSituation = totalServiceAuthorizationSituation
        self.organizationalUnitSummary = organizationalUnitSummary
        #print (self.getName(), organizationalUnitSummary)

    def fetchDetails(self, organizationClient):
        self.fetchAttatchedPolicies(organizationClient)
        #fetchAccountsUnderOU

    def fetchAttatchedPolicies(self, organizationClient):

        response = organizationClient.list_policies_for_target(
            TargetId=self.id,
            Filter='SERVICE_CONTROL_POLICY'
        )

        allPolicies = response['Policies']
        for policyInfo in allPolicies:
            policyCompleteInfo = organizationClient.describe_policy(
                PolicyId=policyInfo['Id']
            )

            policy = ServiceControlPolicy(policyCompleteInfo)

            self.policies.append(policy)

    def getName(self):
            return self.name

class RootOrganizationalUnit(OrganizationalUnit):
    def __init__(self, data):
        OrganizationalUnit.__init__(self, data)

        self.isRoot = True
        self.policyTypes = data['PolicyTypes']




class ServiceControlPolicy:
    def __init__(self, policyCompleteInfo):
        self.policyContent = policyCompleteInfo['Policy']['Content']

        policySummary = policyCompleteInfo['Policy']['PolicySummary']
        self.id = policySummary['Id']
        self.arn = policySummary['Arn']
        self.name = policySummary['Name']
        self.description = policySummary['Description']
        self.type = policySummary['Type']
        self.awsManaged = policySummary['AwsManaged']

    def getPolicyStatements(self):
        # Returns list of statements. Each statement is a pair of effect, action, resource
        policyContent = json.loads(self.policyContent)
        statements = policyContent['Statement']
        return statements
