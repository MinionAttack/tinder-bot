# -*- coding: utf-8 -*-

# Login #

more_login_options = '/html/body/div[2]/div/div/div/div/div[3]/span/button'

login_with_facebook = '/html/body/div[2]/div/div/div/div/div[3]/span/div[2]/button'

login_with_facebook_expanded = '/html/body/div[2]/div/div/div/div/div[3]/span/div[3]/button'

email_input = '//*[@id="email"]'

password_input = '//*[@id="pass"]'

login = '//*[@id="u_0_0"]'

# Permission request #

location_permission = '/html/body/div[2]/div/div/div/div/div[3]/button[1]'

notification_permission = '/html/body/div[2]/div/div/div/div/div[3]/button[1]'

cookies_permission = '/html/body/div[1]/div/div[2]/div/div/div[1]/button'

# Match cardboards #

cardboard = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div[1]'

photos_selector = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div[2]'

photo_selector_button = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div[2]/button[$index]'

actual_photo_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div[1]/div/div[$index]/div/div'

one_photo_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div/div/div/div/div'

candidate_name_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[6]/div/div[1]/div/div/span'

candidate_age_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[6]/div/div[1]/div/span'

# With 'actual_photo' you can get the photo_preview of a video but the real paths of the photo and the respective video
# are this two. The video is in MP4 format.
actual_photo_video_preview = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div[1]/div/div[$index]/div/div[1]'
actual_video = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[1]/div[3]/div[1]/div[1]/div/div[$index]/div/div[2]/video'

buttons_panel = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[2]'

like = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[2]/div[4]/button'

dislike = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[1]/div/div[2]/div[2]/button'

# Gold blurry matches #

matches_tab = '//*[@id="match-tab"]'

grouped_matches = '/html/body/div[1]/div/div[1]/div/aside/nav/div/div/div/div[2]/div[1]/div[1]/div/a'

blurry_list = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div[2]/div'

# Chats with matched profiles #

messages_tab = '//*[@id="messages-tab"]'

matched_profiles_list = '/html/body/div[1]/div/div[1]/div/aside/nav/div/div/div/div[2]/div[2]/div[2]'

matched_profile_photos_selector = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[1]/span/a/div/div[2]'

matched_profile_photo_selector_button = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[1]/span/a/div/div[2]/button[$index]'

matched_profile_photo_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[1]/span/a/div/div[1]/div/div[$index]/div/div/div'

matched_profile_one_photo_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[1]/span/a/div/div/div/div/div/div/div'

matched_profile_name_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[1]/div/div[1]/div/h1'

matched_profile_age_path = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[2]/div/div[1]/div/div/div[2]/div[1]/div/div[1]/span'

chat_text_area = '//*[@id="chat-text-area"]'

send_chat_text_area = '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div[1]/div/div/div[3]/form/button'

# Pop-ups #

# This pop-up was used during COVID-19
passport_popup = '/html/body/div[2]/div/div/div[2]/button'

gold_popup = '/html/body/div[2]/div/div/div[2]/button[2]'

get_tinder_plus = '/html/body/div[2]/div/div/div[3]/button[2]'

advertisement_popup = ''

match_popup = '/html/body/div[1]/div/div[1]/div/main/div[2]/div/div/div[1]/div/div[3]/a'
