import os
import boto3
import json
import logging
import botocore

#EC2 Client
client = boto3.client('ec2')
resclient = boto3.resource('ec2')

#Change as per SES
sourceadd = "abc@def.com"
CHARSET = "UTF-8"
AWS_REGION = "us-east-1"

#SES Client
sesclient = boto3.client('ses',region_name=AWS_REGION)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#Option for change if required.
requiredtags = ["ENVIRONMENT","NAME"]

#Stop after n number of hours
hours = 6

def lambda_handler(event='',context=''):
    allinstances = getallinstances()
    withtagdetails = gettagdetails(allinstances)
    logger.info("AllinstancesDetails"+str(withtagdetails))
    for eachinstance,detailsofeach in withtagdetails.items():
        if detailsofeach['status'] != 'stopped':
            if 'time' not in detailsofeach['tags']:
                req = []
                for each in requiredtags:
                    if each.lower() not in detailsofeach['tags']:
                        req.append(each)
                if req:
                    sendmail(eachinstance,detailsofeach,"MissingTags",req)
                    logger.info(eachinstance+": Email sent for missing tags "+','.join(req))
                    response = client.create_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time','Value': '0'}])
                    response = client.create_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'createdbyold','Value': detailsofeach['tags']['created by']}])
                    detailsofeach['tags']['time'] = 0
                    detailsofeach['tags']['createdbyold']=detailsofeach['tags']['created by']
            else:
                #Restart the process if created by is changed.
                if detailsofeach['tags']['created by'] != detailsofeach['tags']['createdbyold']:
                    sendmail(eachinstance,detailsofeach,"MissingTags",req)
                    logger.info(eachinstance+": Email sent for missing tags "+','.join(req))
                    response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time'}])
                    response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'createdbyold'}])
                    response = client.create_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time','Value': '0'}])
                    response = client.create_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'createdbyold','Value': detailsofeach['tags']['created by']}])
                    detailsofeach['tags']['time'] = 0
                    detailsofeach['tags']['createdbyold']=detailsofeach['tags']['created by']
                    continue
                    
                detailsofeach['tags']['time']=int(detailsofeach['tags']['time'])+1
                response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time'}])
                response = client.create_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time','Value': str(detailsofeach['tags']['time'])}])
                req = []
                #Check if tags are updated.
                for each in requiredtags:
                    if each.lower() not in detailsofeach['tags']:
                        req.append(each)
                if not req:
                    logger.info(eachinstance+": All missing tags are Updated and is not going to be Terminated! :)")
                    response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time'}])
                    response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'createdbyold'}])
                else:
                    if detailsofeach['tags']['time'] >= hours:
                        whathappend = closeinstance(eachinstance)
                        if whathappend == 0:
                            logger.info(eachinstance+": Could not to be Terminated! :(")
                            logger.info(eachinstance+": It will be retried in an hour")
                        else:
                            sendmail(eachinstance,detailsofeach,"Stopped",req)
                            response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'time'}])
                            response = client.delete_tags(DryRun = False,Resources=[eachinstance],Tags=[{'Key': 'createdbyold'}])
    return(1)

#Getting all Instances
def getallinstances():
    response = client.describe_instance_status(IncludeAllInstances = True)
    instances = response['InstanceStatuses']
    instanceinfo = {}
    for eachinstance in instances:
        instanceinfo[eachinstance['InstanceId']] = eachinstance['InstanceState']['Name']
    return(instanceinfo)

#Getting tags of all Instances
def gettagdetails(allinstances):
    allinstanceswithtags= {}
    for eachinstance,status in allinstances.items():
        alldetails = {}
        tagsi = {}
        instancetags = resclient.Instance(eachinstance)
        for eachtag in instancetags.tags:
            tagsi[eachtag['Key'].lower()] = eachtag['Value']
        alldetails['tags'] = tagsi
        alldetails['status'] = status
        allinstanceswithtags[eachinstance] = alldetails
    return(allinstanceswithtags)

#Check type of mail
def sendmail(eachinstance,detailsofeach,typeofmail,req):
    body = ""
    subject = ""
    if typeofmail == "Stopped":
        subject = "Instance of instanceID "+eachinstance+" has been Stopped."
        body = "Dear user,\n\nWe have stopped the instance with the InstanceID "+eachinstance+" which was created by you as it did not contain the following tag(s) "+','.join(req)+". Please make sure you create the tags before restarting the instance if you do not want the instance to be stopped again. \n\n Sincerely, \nAccount Owner :)"
        actualmailsend(eachinstance,detailsofeach['tags']['created by'],body,subject)
    if typeofmail == "MissingTags":
        subject = "Instance of instanceID "+eachinstance+" will be Stopped."
        body = "Dear user,\n\nThe instance with the InstanceID "+eachinstance+" which was created by you will be Stopped in "+str(hours)+" Hours as it does not contain the following tag(s) "+','.join(req)+". \nYou got this mail as the created by tag has your email address in it. If you think this is a misunderstanding, Please update the created by tag of the Instance. \n\n Sincerely, \n Account Owner :)"
        actualmailsend(eachinstance,detailsofeach['tags']['created by'],body,subject)
    
#Close an Instance
def closeinstance(instanceID):    
    try:
        instanceIDs = [instanceID]
        response = client.stop_instances(InstanceIds=instanceIDs)
    except botocore.exceptions.ClientError as e:
        logger.info(e)
        return(0)
    return(1) #Successfully Stopped
    
#Send Mail
def actualmailsend(eachinstance,to,body,subject):
    try:
        #Provide the contents of the email.
        response = sesclient.send_email(
            Destination={
                'ToAddresses': [to],
            },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': body,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject,
                },
            },
            Source=sourceadd,
        )
    except botocore.exceptions.ClientError as e:
        logger.info(eachinstance+": Exception in sending mail to "+to)
        logger.info(e)
    else:
        logger.info(eachinstance+": Email sent successfully and Message ID:"+response['MessageId'])
