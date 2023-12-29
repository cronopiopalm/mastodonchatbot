import argparse
from mastodon import Mastodon
import html2text
from openai import OpenAI
import os
import json

# Setup openai
client = OpenAI(api_key='...')

# Setup Mastodon
mastodon = Mastodon(
    access_token = '...',
    api_base_url = '...'
)

#  !!!!! Record this bot's mastodon ID here
# this is needed to load conversations correctly
my_id = ...

# Optional: load and write usage as json
with open('usage_dict.json', 'r', encoding='utf-8') as fp:
    usage_dict = json.load(fp)

# Required: load checkpoint (checkpoint has to be stored externally)
with open('checkpoint.json', 'r') as fp:
    checkpoint = json.load(fp)

# Main loop: check through new mentions
def iterate_through():

	# grab all noficiations since last one, mentions only
	notifications = mastodon.notifications(since_id=checkpoint, mentions_only=True)
	# if no new notification, quit
	if len(notifications)==0:
		return
	# if have new notification, record the latest, note that notifications are FILO
	with open('checkpoint.json', 'w') as fp:
		json.dump(notifications[0]['id'],fp)

	for post in notifications:
		# skip other notifications	
		if post['type']!='mention':
			continue
		
		print("chating with ",post["status"]["account"]["display_name"],post['id'])
		# Format input
		h=html2text.HTML2Text()
		h.ignore_links = True
		inputtext = h.handle(post["status"]["content"]).strip("\n")
		# remove @
		inputtext = ' '.join(word for word in inputtext.split(' ') if not word.startswith('@'))
    # setup system prompt
		messages = [{"role": "system", "content": "你是一个非常实用的 AI 助手"},]	

		# load context
		if post['status']['in_reply_to_id']:
      # load chat history as dictionary {id: content}
			context_dict = [[x["account"]["id"], h.handle(x["content"]).strip("\n")] for x in mastodon.status_context(post['status']['id'])['ancestors']]
			for d in context_dict:
				# if author is not me, log as user
				if d[0]!=my_id:
					messages.append({"role": "user", "content": d[1]},)
				# if author is me, log as assistant
				else:
					messages.append({"role": "assistant", "content": d[1]},)

		messages.append({"role": "user", "content": inputtext},)
		chat_completion = client.chat.completions.create(
			model="gpt-4-1106-preview", 
			messages=messages
		)
		# get the reply
		reply = chat_completion.choices[0].message.content
		# Optional: record usage
		token_counter = chat_completion.usage.total_tokens
		usage_dict[post["status"]["account"]["display_name"]] = usage_dict.get(post["status"]["account"]["display_name"],0)+token_counter
		# toot
		mastodon.status_reply(post['status'],reply)
		# record done
	# Optional: when all finished, write  usage to dict
	with open('usage_dict.json', 'w', encoding='utf-8') as fp:
		json.dump(usage_dict,fp, ensure_ascii=False)

if __name__ == "__main__":
	iterate_through()
