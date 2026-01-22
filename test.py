# Raw string from frontend
import json


raw_settings = "{\"visibility\":\"Public\",\"showLikes\":true,\"enableComments\":true,\"allowSharing\":true,\"showLocation\":false,\"pinned\":false,\"ageRestriction\":\"Everyone\",\"disableReactions\":false}"

# Convert string to dict
settings_dict = json.loads(raw_settings)

print(settings_dict)
