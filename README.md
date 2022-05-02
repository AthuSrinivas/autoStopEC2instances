# autoStopEC2instances
This is a repository for a lambda function to automatically stop EC2 Instances based on tags and time.
*It runs everyhour to check for running EC2 instances and checks if required tag(s) are added.
*If the required tag(s) are not added, it sends a notification mail to the email present in "created by" tag of the Instance.
*If the tags are not added even after 6 hours of the notification, the instance is terminated and the same is notified. 

Development Steps:

1. Go to Identity and Access Management (IAM) console and select Roles.
2. Select create Role.
3. Select AWS Service under Trusted entity type and Lambda under usecases.
4. Search and select the following policies
  *AWSLambdaBasicExecutionRole
  *AWSLambdaEdgeExecutionRole
  *pinpoint-email-ers-
  *AmazonEC2FullAccess
  *CloudWatchFullAccess
  *AmazonSESFullAccess
  *CloudWatchLogsFullAccess
5. Give an appropriate Rolename
6. Open the Functions page of the Lambda console.
7. Make sure "Author from Scratch" is selected.
8. For Function name, enter {function name}.
9. For Runtime, confirm that Python 3.9 is selected.
10. Under Change default execution role, Select existing Role which was created and next.
11. Add Trigger > "Event Bridge" > Create New Rule > Enter Rule name > Scheduled expression > "rate(1 hour)" > Add
12. Under code, Either copy code from lambda_function.py to code body or Upload the given zip file to it.
13. Configure SES for email's to send.
14. Configure Pinpoint for email's to be recieved when the script is invoked.
15. Mandatory Edits:
  *Sourceadd: Change Source Address to email from which the notifications are sent.
  *AWS_REGION: As per configuration.
16. Let the Script do it's job.

Note:
Change Required tags and number of hours as per neccessary.
Check CloudwatchLogs for additional logs.
