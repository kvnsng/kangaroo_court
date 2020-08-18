import os
from time import sleep

import requests
from flask import abort, Flask, jsonify, request, make_response, Response
import json
from slack import WebClient
import boto3
from datetime import datetime
import pandas as pd

app = Flask(__name__)
client = WebClient(token=os.environ['SLACK_BOT_TOKEN'])

def is_request_valid(request):
    is_token_valid = request.form['token'] == os.environ['SLACK_VERIFICATION_TOKEN']
    is_team_id_valid = request.form['team_id'] == os.environ['SLACK_TEAM_ID']
    return is_token_valid and is_team_id_valid

@app.route('/kangaroo_court', methods=['POST'])
def kangaroo_court():
    if not is_request_valid(request):
        abort(400) 
    trigger_id = request.form['trigger_id']
    #callback_id = request.form['callback_id']    
    view = {
    "type": "modal",
    "callback_id": "modal-identifier",
	"title": {
		"type": "plain_text",
		"text": "Kangaroo Court",
		"emoji": True
	},
	"submit": {
		"type": "plain_text",
		"text": "Submit",
		"emoji": True
	},
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": True
      },
	"blocks": [
		{
			"type": "input",
            "block_id": "defendant",
			"element": {
				"type": "multi_users_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Defendant",
					"emoji": True
				}
			},
			"label": {
				"type": "plain_text",
				"text": "Defendant",
				"emoji": True
			}
		},
        {
			"type": "input",
            "block_id": "anonymous",
			"element": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Yes or No",
					"emoji": True
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "Yes",
							"emoji": True
						},
						"value": "yes"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "No",
							"emoji": True
						},
						"value": "no"
					}
				]
			},
			"label": {
				"type": "plain_text",
				"text": "Want to be anonymous?",
				"emoji": True
			}
		},
		{
			"type": "input",
            "block_id": "credOrFine",

			"element": {
				"type": "static_select",
				"placeholder": {
					"type": "plain_text",
					"text": "Credit or Fine",
					"emoji": True
				},
				"options": [
					{
						"text": {
							"type": "plain_text",
							"text": "Credit",
							"emoji": True
						},
						"value": "credit"
					},
					{
						"text": {
							"type": "plain_text",
							"text": "Fine",
							"emoji": True
						},
						"value": "fine"
					}
				]
			},
			"label": {
				"type": "plain_text",
				"text": "Credit or Fine",
				"emoji": True
			}
		},
		{
			"type": "input",
             "block_id": "fineAmount",
			"element": {
				"type": "plain_text_input",
				"placeholder": {
					"type": "plain_text",
					"text": "Amount in dollars ($)",
					"emoji": True
				}
			},
			"label": {
				"type": "plain_text",
				"text": "Amount",
				"emoji": True
			}
		},
		{
			"type": "input",
             "block_id": "act",
			"element": {
				"type": "plain_text_input",
				"multiline": True,
				"placeholder": {
					"type": "plain_text",
					"text": "What did the defendants do?",
					"emoji": True
				}
			},
			"label": {
				"type": "plain_text",
				"text": "Act",
				"emoji": True
			}
		}
	]
}
    open_view = client.views_open(trigger_id = trigger_id,
                                    view=view)
    #view_id = open_dialog['view']['id']
    return make_response("", 200)

@app.route('/submit', methods=['POST'])
def submit():
    #client.views_update(trigger_id= )
    #
    payload = json.loads(request.form["payload"])
    print(payload)
    user = payload['user']['id']
    plaintiff = payload['user']['id']
    blocks = payload['view']['blocks']
    view_state = payload['view']['state']['values']
    
    
    dynamodb = boto3.resource('dynamodb',
                              aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                              aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], 
                              region_name='us-east-2',
                              use_ssl=False)
    
    DBclient = boto3.client('dynamodb')
    tableKangarooCourt = dynamodb.Table('kangaroo_court')
    response = tableKangarooCourt.scan()
    currentCnt = int(response['Count'])
    if currentCnt == 0:
        newCnt = 1
    else:
        newCnt = currentCnt + 1
        
    eventDateTime = (datetime.now()).strftime("%Y%m%d")
    #print(blocks)
    #print(view_state)
    for block in blocks:
        
        if block['type'] == 'input':
            block_id = block['block_id']
            action_id = block['element']['action_id']
        
        if block['block_id'] == 'defendant':
            
            selectedUsers = view_state[block_id][action_id]['selected_users']
            selUserString = ''
            for i in range(len(selectedUsers)):
                if i+1 == len(selectedUsers):
                    selUserString += f'<@{selectedUsers[i]}>'
                else:
                    selUserString += f'<@{selectedUsers[i]}>, '
                    
        elif block['block_id'] == 'credOrFine':
            
            credOrFine = view_state[block_id][action_id]['selected_option']['text']['text']
        
        elif block['block_id'] == 'fineAmount':
            
            fineAmount = view_state[block_id][action_id]['value']
            fineAmount = ''.join(filter(str.isdigit, fineAmount))
            
        elif block['block_id'] == 'act':
            
            act = view_state[block_id][action_id]['value']
        
        elif block['block_id'] == 'anonymous':
            anonymous = view_state[block_id][action_id]['selected_option']['value']
            if anonymous == 'yes':
                plaintiff = 'Anonymous'
            elif anonymous == 'no':
                continue
                
    tableKangarooCourt.put_item(
                                Item={
                                      'courtCaseCnt': int(newCnt),
                                      'courtSubmitDate': eventDateTime,
                                      'plaintiff': plaintiff,
                                      'defendant': selectedUsers,
                                      'credOrFine': credOrFine,
                                      'fineAmount': fineAmount,
                                      'act': act
                                })
    
    client.chat_postEphemeral(user=user,
                            channel='#kangaroo_court',
                            text=f'*Plaintiff*:<@{plaintiff}>\n *Defendant*: {selUserString}\n *Credit or Fine*: {credOrFine}\n *Amount*: {fineAmount}\n *Act*: {act}')
    #if not is_request_valid(payload):
    #    abort(400)    
    
    #if payload["type"] == "view_submission":
    #    print(payload["state"])
    #client.chat_postMessage(channel='#testbot',
    #                            text=f'{}')
        
    return make_response("",200)

@app.route('/judgement_day', methods=['POST'])
def judgement_day():
    userID = request.form['user_id']
    if userID not in ['UDZ1W9XP1', 'UG5DHURTP']:
        client.chat_postEphemeral(user=userID,
                            channel='#kangaroo_court',
                            text="You're not the judge, you sneaky fox!")
        return make_response("", 200)
    else:
        # begin judging
        blocks = [		
            {
			"type": "divider"
            },
    		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "*Cases brought to your honor, judge Sonabend*"
                    },
                
            },
            {
			"type": "divider"
            }
    
         ]
        dynamodb = boto3.resource('dynamodb',
                              aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                              aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], 
                              region_name='us-east-2',
                              use_ssl=False)
        DBclient = boto3.client('dynamodb')

        tableKangarooCourt = dynamodb.Table('kangaroo_court')
        response = tableKangarooCourt.scan()
        df = pd.DataFrame(response['Items'])
        df = df.sample(frac=1)
        print(df)
        for idx, r in df.iterrows():
            act = r.act
            courtCaseNumber = r.courtCaseCnt
            courtSubmitDate = r.courtSubmitDate
            plaintiff = r.plaintiff
            fineAmount = r.fineAmount
            credOrFine = r.credOrFine
            defendants = r.defendant
            defendantString = ''
            for i in range(len(defendants)):
                if i+1 == len(defendants):
                    defendantString += f'<@{defendants[i]}>'
                else:
                    defendantString += f'<@{defendants[i]}>, '
            credOrFine = r.credOrFine

            blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Plaintiff: <@{plaintiff}>"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "|"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"Defendant: {defendantString}"

                        },
                        {
                            "type": "mrkdwn",
                            "text": "|"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"{credOrFine}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": "|"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"Amount: {fineAmount}"
                        }
                    ]
                })
            blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{act}*"
                    }
                })
            blocks.append({
                    "type": "divider"
            })
        client.chat_postEphemeral(user=userID,
                            channel='#kangaroo_court',
                            blocks=blocks)
        
        return make_response("", 200)

@app.route('/mycomplaints', methods=['POST'])
def my_complaints():
    userID = request.form['user_id']
    
    dynamodb = boto3.resource('dynamodb',
                              aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
                              aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'], 
                              region_name='us-east-2',
                              use_ssl=False)
    
    DBclient = boto3.client('dynamodb')
    tableKangarooCourt = dynamodb.Table('kangaroo_court')
    response = tableKangarooCourt.scan()
    df = pd.DataFrame(response['Items'])
    
    df = df[df['plaintiff'] == userID]
    
    for idx, r in df.iterrows():
        selUserString = ''
        defendants = list(r.defendant)
        for i in range(len(defendants)):
            if i+1 == len(defendants):
                selUserString += f'<@{defendants[i]}>'
            else:
                selUserString += f'<@{defendants[i]}>, '
        client.chat_postEphemeral(user=userID,
                            channel='#kangaroo_court',
                            text=f'*Plaintiff*:<@{r.plaintiff}>\n *Defendant*: {selUserString}\n *Credit or Fine*: {r.credOrFine}\n *Amount*: {r.fineAmount}\n *Act*: {r.act}')
    print(request.get_data())
    return make_response("", 200)
    
if __name__ == "__main__":
    app.run()