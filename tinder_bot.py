#!/usr/bin/python3
# -*- coding: utf-8 -*-
try:
    import os
    import pathlib
    import re
    import requests
    import secrets
    import shutil
    import stat
    from statistics import median, StatisticsError
    import sys
    from time import sleep

    from logger import logger
    from predict import beauty_predict
    from string import Template
    import face_recognition

    from crontab import CronTab
    from selenium import webdriver
    from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException
    from selenium.common.exceptions import StaleElementReferenceException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait

    from resources.constants import ARIA_LABEL_CHAT, BLURRED_ITEM_CLASS, BLURRED_PHOTO_CLASS, CRONTAB_BOT_COMMENT, DEFAULT_CHAT_MESSAGES
    from resources.constants import EXPAND_BUTTON_TEXT, GOLD_FOLDER, MATCHED_FOLDER, PASSWORD, READ_TEXT_CHAT, SENT_TEXT_CHAT, SILENT_MODE
    from resources.constants import SCORE_THRESHOLD, THUMBNAIL_ORIGINAL_SIZE_MAPPING, TEMP_FOLDER, UNKNOWN_SUFFIX, USERNAME
    from resources.constants import WAIT_MATCH_ANSWER, WEBSITE_URL

    from resources.firefox_xpaths import actual_photo_path, actual_video, blurry_list, buttons_panel
    from resources.firefox_xpaths import candidate_age_path, candidate_name_path, cardboard, chat_text_area
    from resources.firefox_xpaths import cookies_permission, dislike, email_input, get_tinder_plus, gold_popup
    from resources.firefox_xpaths import grouped_matches, like, login, location_permission, login_with_facebook
    from resources.firefox_xpaths import login_with_facebook_expanded, match_popup, matched_profiles_list
    from resources.firefox_xpaths import matched_profile_age_path, matched_profile_name_path
    from resources.firefox_xpaths import matched_profile_one_photo_path, matched_profile_photos_selector
    from resources.firefox_xpaths import matched_profile_photo_path, matched_profile_photo_selector_button, matches_tab
    from resources.firefox_xpaths import messages_tab, more_login_options, notification_permission, one_photo_path
    from resources.firefox_xpaths import passport_popup, password_input, photos_selector, photo_selector_button
    from resources.firefox_xpaths import send_chat_text_area
except ModuleNotFoundError:
    print('Something went wrong while importing dependencies. Please, check the requirements file.')
    sys.exit(1)


class TinderBot:
    UPDATE_XPATH_STRING = 'The item could not be found at the specified path. The XPaths file needs to be updated.'
    PHOTO_FOLDER_NAME = Template('$name - $age year(s) - $photos photo(s)')

    def __init__(self):
        logger.info('Initializing bot.')

        parent_folder = pathlib.Path(__file__).parent.absolute()
        # Create gold matches folder
        self.gold_matches_folder = os.path.join(parent_folder, GOLD_FOLDER)
        pathlib.Path(self.gold_matches_folder).mkdir(exist_ok=True)
        # Create matched folder
        self.matched_folder = os.path.join(parent_folder, MATCHED_FOLDER)
        pathlib.Path(self.matched_folder).mkdir(exist_ok=True)
        # Create temporary folder
        self.temporary_folder = os.path.join(parent_folder, TEMP_FOLDER)
        pathlib.Path(self.temporary_folder).mkdir(exist_ok=True)

        self.url = WEBSITE_URL
        self.free_limit_reached = False
        self.likes_counter = 0
        self.dislikes_counter = 0
        self.options = self.configure_firefox_options()
        # We wait to start the driver and the browser instance until we check if the credentials are valid.
        self.driver = None
        self.web_driver_wait = None

    @staticmethod
    def configure_firefox_options():
        logger.info('Setting Firefox preferences.')

        options = Options()
        # Run Firefox with no GUI
        if SILENT_MODE:
            options.add_argument('--headless')
        # Allow all cookies
        options.set_preference('network.cookie.cookieBehavior', 0)
        # Sometimes Facebook login window fails because it says that cookies are not enabled
        options.set_preference('network.cookieSettings.unblocked_for_testing', 1)
        # Allow notifications. This avoids Firefox built-in notification request window.
        options.set_preference('permissions.default.desktop-notification', 1)
        # Show desktop notifications
        options.set_preference('dom.webnotifications.enabled', 1)
        # Background updates
        options.set_preference('dom.push.enabled', 1)
        # Allow geolocation. This avoids Firefox built-in location request window.
        options.set_preference('permissions.default.geo', 1)

        return options

    def check_user_constants(self):
        logger.info('Checking user constant values.')

        if self.check_credentials():
            if self.check_score_threshold():
                # Here you can start the browser instance.
                logger.info('Possible valid user constants detected. starting driver.')
                self.driver = webdriver.Firefox(firefox_options=self.options)
                self.web_driver_wait = WebDriverWait(self.driver, timeout=10, poll_frequency=1, ignored_exceptions=[])
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def check_score_threshold():
        logger.info('Checking user score threshold value.')

        try:
            float(SCORE_THRESHOLD)
            return True
        except ValueError:
            logger.error('The score threshold value is not correct. Please check the constants.py file.')
            return False

    def check_credentials(self):
        logger.info('Checking user credentials.')

        stripped_username = USERNAME.strip()
        if len(stripped_username) > 0 and len(PASSWORD.strip()) > 0:
            if self.is_valid_email(stripped_username):
                return True
            else:
                logger.error('The e-mail format is not correct. Please check the constants.py file.')
                return False
        else:
            logger.error('Please, provide the login credentials in constants.py file.')
            return False

    # https://stackoverflow.com/a/49226861/3522933
    @staticmethod
    def is_valid_email(email):
        if len(email) > 7:
            return bool(re.match(r'^.+@(\[?)[a-zA-Z0-9-.]+.([a-zA-Z]{2,3}|[0-9]{1,3})(]?)$', email))
        else:
            return False

    def login(self):
        logger.info('Logging on Tinder via Facebook.')

        self.driver.get(self.url)
        # Sometimes the Facebook login option is hidden in 'More options'. We need first to check if it is hidden and if it fails we know
        # that it is displayed.
        facebook_xpath = None
        try:
            self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, more_login_options)))
            more_options_button = self.driver.find_element_by_xpath(more_login_options)
            # Tinder uses the same button to show more login options as to fix login issues, we need to check in what case we are.
            if more_options_button.text == EXPAND_BUTTON_TEXT:
                more_options_button.click()
                facebook_xpath = login_with_facebook_expanded
            else:
                # The text is 'Trouble Logging In?' so the Facebook login option is already displayed.
                raise NoSuchElementException
        except (TimeoutException, NoSuchElementException):
            logger.warning("Facebook login option displayed. Exception thrown waiting for 'More options'.")
            facebook_xpath = login_with_facebook
        finally:
            self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, facebook_xpath)))
            facebook_button = self.driver.find_element_by_xpath(facebook_xpath)
            facebook_button.click()

        # Wait until the Facebook login pop-up window is loaded
        number_of_windows = len(self.driver.window_handles)
        while number_of_windows < 2:
            number_of_windows = len(self.driver.window_handles)

        # Switch to login pop-up window
        base_window = self.driver.window_handles[0]
        popup_window = self.driver.window_handles[1]
        self.driver.switch_to.window(popup_window)

        self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, email_input)))
        try:
            email_text_area = self.driver.find_element_by_xpath(email_input)
            email_text_area.send_keys(USERNAME)

            self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, password_input)))

            password_text_area = self.driver.find_element_by_xpath(password_input)
            password_text_area.send_keys(PASSWORD)

            login_button = self.driver.find_element_by_xpath(login)
            login_button.click()
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('The login operation cannot be performed.')
            self.remove_crontab_entry()
            self.exit()

        # Return to main window
        self.driver.switch_to.window(base_window)

        # Sometimes the Facebook login window complains that cookies are not enabled and the bot cannot log in. If this happens, the bot
        # turns off and is configured to automatically restart.
        if len(self.driver.window_handles) > 1:
            logger.error('Cookies error on Facebook login window.')
            self.check_crontab_entry()
            self.exit()

    def auto_swipe(self):
        logger.info('Starting to swiping.')

        free_matches_limit_reached = False
        number_of_swipes = 0
        limit_of_attempts = 6  # 6 * 10 seconds = 60 seconds of waiting
        actual_attempt = 1

        while actual_attempt <= limit_of_attempts and not free_matches_limit_reached:
            try:
                # This is related with Tinder showing the tutorial of how swipe cardboards with gestures. We need to wait until the tutorial
                # ends and the cardboard is available to click. 5 seconds is not enough, the tutorial lasts about 6 seconds so I give a
                # margin waiting for 8 seconds.
                self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, cardboard)))
                cardboard_section = self.driver.find_elements_by_xpath(cardboard)
                buttons_panel_section = self.driver.find_elements_by_xpath(buttons_panel)

                if len(cardboard_section) > 0 and len(buttons_panel_section) > 0:  # Potential matches are shown.
                    # We need time so the cardboard loads and at least the first photo too.
                    self.simulate_human_response_time()
                    validation_results = self.detect_valid_profile()
                    free_matches_limit_reached = validation_results['limit_reached']
                    profile_photos = validation_results['photos']
                    valid_profile = validation_results['valid']
                    if not free_matches_limit_reached:
                        try:
                            self.simulate_human_match_selection(profile_photos, valid_profile)
                            number_of_swipes += 1
                            logger.info('{} profile(s) swiped. Likes: {} - Dislikes: {}.'.format(number_of_swipes, self.likes_counter,
                                                                                                 self.dislikes_counter))
                        # If you do not validate the profiles you need to catch here the pop-up of out of likes.
                        except ElementClickInterceptedException:  # A wild pop-up appeared!
                            free_matches_limit_reached = self.find_popup_to_close()
                            logger.info('Free matches limit reached. Try again later.')
            except TimeoutException:
                logger.info('Search animation in progress or cookies error on login screen. Attempt {} of {}'.format(actual_attempt,
                                                                                                                     limit_of_attempts))
                actual_attempt += 1

        self.free_limit_reached = free_matches_limit_reached

    def detect_valid_profile(self):
        logger.info('Detect if it is a valid profile.')

        free_matches_limit_reached, profile_data = self.collect_profile_photos()
        if not free_matches_limit_reached:
            if len(profile_data['photos']) > 0:
                valid_photos = self.detect_human_photos(profile_data)
                if len(valid_photos) > 0:
                    return {'limit_reached': free_matches_limit_reached, 'photos': valid_photos, 'valid': True}
                else:
                    return {'limit_reached': free_matches_limit_reached, 'photos': None, 'valid': False}
            else:
                return {'limit_reached': free_matches_limit_reached, 'photos': None, 'valid': False}
        else:
            return {'limit_reached': free_matches_limit_reached, 'photos': None, 'valid': None}

    def collect_profile_photos(self):
        logger.info('Collecting profile photos to analyze.')

        profile_name = ''
        profile_age = ''
        photos = []
        array_of_buttons = self.driver.find_elements_by_xpath(photos_selector)
        free_matches_limit_reached = False

        # After press Like and getting the pop-up of out of likes, the code does another iteration an tries to validate the same profile but
        # the pop-up obscures it so we need to handle here the exception.
        try:
            # Although the selector is available shortly before the end of the tutorial, the name and age are not.
            self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, candidate_name_path)))
            profile_name = self.driver.find_element_by_xpath(candidate_name_path)
            profile_age = self.driver.find_element_by_xpath(candidate_age_path)
            if len(array_of_buttons) > 0:  # The profile has more than one photo, seems a valid profile.
                logger.info('Found a possible valid profile.')
                # The list of photos is a <div> of <button>. The . at the beginning specifies to find all child nodes.
                selector_of_photos = array_of_buttons[0]
                photos_available = selector_of_photos.find_elements_by_xpath('.//button')
                photos = self.loop_over_photos(photos_available, photo_selector_button, actual_photo_path)
            else:  # Only one photo, can be a non photo profile or a non personal photo.
                self.simulate_human_response_time()
                photo_url = self.get_profile_photo(one_photo_path)
                # This is the URL of the default photo if the user did not upload any photo.
                # https://images-ssl.gotinder.com/0001unknown/640x640_pct_0_0_100_100_unknown.jpg
                if not photo_url.endswith(UNKNOWN_SUFFIX):
                    photos.append(photo_url)
                    logger.info('Unique photo URL: {}.'.format(photo_url))
                else:
                    logger.info('Profile with no photo detected!')
            logger.info('Photo recovery finished for the actual profile.')
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('The photo collection operation cannot be performed.')
            self.remove_crontab_entry()
            self.exit()
        except ElementClickInterceptedException:  # A wild pop-up appeared!
            free_matches_limit_reached = self.find_popup_to_close()
            logger.info('Free matches limit reached. Try again later.')
        except TimeoutException:
            logger.warning('Timeout exception when collecting photos from matching profiles, there could be a network problem.')

        profile_data = {'age': profile_age.text, 'name': profile_name.text, 'photos': photos}

        return free_matches_limit_reached, profile_data

    def loop_over_photos(self, photos_available, photo_selector, selected_photo):
        # Tinder loads the photos on the fly, you only get the actual photo. You never get access to all photos by default so I use the
        # index after click on the selector.
        photos = []
        photo_index = 1  # Tinder starts the index at 1 instead of 0.

        for photo_available in photos_available:
            try:
                self.simulate_human_response_time()
                buttons_locator = (By.XPATH, Template(photo_selector).substitute(index=photo_index))
                self.web_driver_wait.until(ec.element_to_be_clickable(buttons_locator))
                photo_available.click()
                # We need time so the photo of the pressed button loads
                self.simulate_human_response_time()
                logger.info('Getting photo {}.'.format(photo_index))
                photo_url = self.get_profile_photo(selected_photo, photo_index)
                logger.info('Photo {} URL: {}.'.format(photo_index, photo_url))
                photos.append(photo_url)
                photo_index += 1
            except ElementClickInterceptedException:
                logger.warning('Element obscured, it is possible that a profile has answered on the chat. Retrying.')
        return photos

    def detect_human_photos(self, profile_data):
        logger.info('Identifying human faces in profile photos. This process could take a while, be patient.')

        valid_photos = []
        profile_age = profile_data['age']
        profile_name = profile_data['name']
        profile_photos = profile_data['photos']

        details = self.PHOTO_FOLDER_NAME.substitute(name=profile_name, age=profile_age, photos=len(profile_photos))
        for index, photo in enumerate(profile_photos, start=1):
            fetched_photo = self.load_image_from_url(self.temporary_folder, photo, details)
            if fetched_photo is not None:
                details = fetched_photo['details']
                image_name = fetched_photo['image_name']
                fetched_photo_path = os.path.join(self.temporary_folder, details, image_name)
                image = face_recognition.load_image_file(fetched_photo_path)
                face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=0, model="cnn")
                if len(face_locations) > 0:
                    valid_photos.append(fetched_photo)
                    logger.info('Found a human face on photo {}.'.format(index))
                else:
                    logger.info('No human face found on photo {}, discarding photo.'.format(index))

        return valid_photos

    @staticmethod
    def load_image_from_url(storage_path, photo_url, details=None):
        # Sometimes the URL fails to be retrieved so we handle that case here.
        if photo_url is not None and photo_url != 'none':
            logger.info('Fetching image from URL: {}.'.format(photo_url))

            image_name = photo_url.split('_')[1]
            if details is None:
                image_path = os.path.join(storage_path, image_name)
            else:
                image_folder = os.path.join(storage_path, details)
                pathlib.Path(image_folder).mkdir(exist_ok=True)
                image_path = os.path.join(image_folder, image_name)
            try:
                image_data = requests.get(photo_url)

                if image_data.status_code == 200:
                    with open(image_path, 'wb') as file:
                        file.write(image_data.content)
                    return {'details': details, 'image_name': image_name}
                else:
                    logger.warning('Could not fetch image from URL: {}, skipping.'.format(photo_url))
                    return None
            except requests.exceptions.ConnectionError:
                logger.warning('Max retries exceeded with photo {}. Temporary failure in name resolution'.format(photo_url))
                return None
        else:
            logger.warning('A URL for the current photo has not been provided. Skipping.'.format(photo_url))
            return None

    @staticmethod
    def simulate_human_response_time():
        list_of_seconds_to_wait = [1, 1.25, 1.5, 1.75, 2]
        time = secrets.choice(list_of_seconds_to_wait)
        sleep(time)

    def get_profile_photo(self, xpath, index=None):
        if index is not None:
            photo_locator = (By.XPATH, Template(xpath).substitute(index=index))
            photo_xpath = Template(xpath).substitute(index=index)
        else:
            photo_locator = (By.XPATH, xpath)
            photo_xpath = xpath

        photo_url = None
        try:
            self.web_driver_wait.until(ec.element_to_be_clickable(photo_locator))
            selected_photo = self.driver.find_element_by_xpath(photo_xpath)
            css_property = selected_photo.value_of_css_property('background-image')
            photo_url = css_property.strip('url(\"').strip('\")')
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Cannot perform photo recovery operation.')
            self.remove_crontab_entry()
            self.exit()

        return photo_url

    # I do not need to process the videos, but I did the method to learn how retrieve the videos.
    def get_profile_video(self, index=None):
        if index is not None:
            video_locator = (By.XPATH, Template(actual_video).substitute(index=index))
            video_xpath = Template(actual_video).substitute(index=index)
        else:
            # TODO: Find a profile with only one video
            video_locator = ''
            video_xpath = ''

        video_url = None
        try:
            self.web_driver_wait.until(ec.element_to_be_clickable(video_locator))
            selected_video = self.driver.find_element_by_xpath(video_xpath)
            video_url = selected_video.get_attribute('src')
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Cannot perform video recovery operation.')
            self.remove_crontab_entry()
            self.exit()

        return video_url

    def simulate_human_match_selection(self, photos, is_valid):
        if is_valid:
            punctuations = []
            for photo in photos:
                details = photo['details']
                image_name = photo['image_name']
                punctuation = beauty_predict(self.temporary_folder, details, image_name)
                punctuations.extend(punctuation)
            average_score = self.calculate_average_score(punctuations)
            if average_score < SCORE_THRESHOLD:
                self.press_button(dislike)
                self.dislikes_counter += 1
                logger.info('Swiping left.')
            elif average_score >= SCORE_THRESHOLD:
                self.press_button(like)
                self.likes_counter += 1
                logger.info('Swiping right.')
        else:
            self.press_button(dislike)
            self.dislikes_counter += 1
            logger.info('Invalid profile. Swiping left.')

    @staticmethod
    def calculate_average_score(punctuations):
        logger.info('Calculate the average score for the actual profile.')

        average_score = 0
        try:
            # We use the median to avoid any influence of the photos where the person is with more people, because that people could distort
            # the actual score due to a score of their face much higher or much lower than the profile's person.
            average_score = median(punctuations)
            logger.info('Average profile score: {:.2f}. Current threshold is: {:.2f}.'.format(average_score, SCORE_THRESHOLD))
        except StatisticsError:
            logger.warning('The median of empty data cannot be calculated.')

        return average_score

    def press_button(self, xpath):
        try:
            locator = (By.XPATH, xpath)
            self.web_driver_wait.until(ec.element_to_be_clickable(locator))
            button = self.driver.find_element_by_xpath(xpath)
            button.click()
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Cannot perform press button operation.')
            self.remove_crontab_entry()
            self.exit()

    def find_popup_to_close(self):
        closeable_popups = {'get_tinder_plus': get_tinder_plus, 'gold': gold_popup, 'match': match_popup}
        free_matches_limit_reached = False

        for name, value in closeable_popups.items():
            try:
                logger.info('Closing [{}] pop-up.'.format(name))
                self.close(value)
                if name == 'get_tinder_plus':
                    free_matches_limit_reached = True
                    break
            except NoSuchElementException:
                logger.error('Failed to close [{}] pop-up.'.format(name))

        return free_matches_limit_reached

    def remove_photo_folder(self, path):
        logger.info('Removing photo folder: {}.'.format(path))

        try:
            shutil.rmtree(path, onerror=self.remove_readonly_files_windows)
        except OSError:
            logger.error('Failed remove photo on Windows, retrying.')

    # See https://docs.python.org/3/library/shutil.html#rmtree-example
    @staticmethod
    def remove_readonly_files_windows(func, path, _):
        # Clear the readonly bit and reattempt the removal
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def close_permission_popups(self):
        logger.info('Trying to close permission pop-ups.')

        # At the moment, location and notification paths are identical but this could change in the future so we need to keep the order.
        # But in Python 3.7+ the insertion-order preservation nature of dict objects has been declared to be an official part of the Python
        # language spec so we do not need to use an OrderedDict for this. https://docs.python.org/3/whatsnew/3.7.html
        permission_popups = {'location': location_permission, 'notifications': notification_permission, 'cookies': cookies_permission}
        for name, value in permission_popups.items():
            try:
                self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, value)))
                logger.info('Trying to close [{}] pop-up.'.format(name))
                self.close(value)
            except TimeoutException:
                logger.warning('Timeout exception waiting for [{}] pop-up.'.format(name))
            except NoSuchElementException:
                logger.error('Failed to close [{}] pop-up.'.format(name))

    def close_covid_popup(self):
        self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, passport_popup)))
        self.close(passport_popup)

    def close(self, popup_xpath):
        try:
            popup = self.driver.find_element_by_xpath(popup_xpath)
            popup.click()
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Cannot perform close operation.')
            self.remove_crontab_entry()
            self.exit()

    def switch_to_tab(self, tab_xpath, name):
        logger.info('Switching to {} tab.'.format(name))

        try:
            tab_locator = (By.XPATH, tab_xpath)
            self.web_driver_wait.until(ec.element_to_be_clickable(tab_locator))
            tab_button = self.driver.find_element_by_xpath(tab_xpath)
            tab_button.click()
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Cannot perform switch tab operation.')
            self.remove_crontab_entry()
            self.exit()

    def review_messages_from_matching_profiles(self, skip_animation=True):
        logger.info('Retrieving chats from the list of matching profiles.')

        try:
            self.switch_to_tab(messages_tab, 'messages')
            list_locator = (By.XPATH, matched_profiles_list)
            self.web_driver_wait.until(ec.element_to_be_clickable(list_locator))
            match_list = self.driver.find_element_by_xpath(matched_profiles_list)
            # The list of matches is a <div> of <a> tags. The . at the beginning specifies to find all child nodes.
            profiles_chats = match_list.find_elements_by_xpath('.//a')
            self.simulate_human_conversation(profiles_chats, skip_animation)
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Skipping sending messages to matching profiles.')
        except TimeoutException:
            logger.warning('Timeout exception when sending messages to matching profiles, there could be a network problem.')

    def simulate_human_conversation(self, profiles_chats, skip_animation):
        logger.info('Send message to matching profiles.')

        name_locator = (By.XPATH, matched_profile_name_path)
        chat_locator = (By.XPATH, chat_text_area)
        send_chat_locator = (By.XPATH, send_chat_text_area)

        # If you use this function without having previously used the auto_swipe function, you will get an error that the
        # xpaths cannot be found because the chat for the pressed match does not load until the tutorial animation finishes.
        if not skip_animation:
            self.wait_end_animation(cardboard)

        if len(DEFAULT_CHAT_MESSAGES) > 0:
            try:
                for profile_chat in profiles_chats:
                    self.simulate_human_response_time()
                    profile_chat.click()
                    self.web_driver_wait.until(ec.element_to_be_clickable(name_locator))
                    profile_name = profile_chat.find_element_by_xpath(matched_profile_name_path).text
                    if WAIT_MATCH_ANSWER:
                        has_answered = self.check_match_answered(profile_name)
                        if not has_answered:
                            continue
                    self.web_driver_wait.until(ec.element_to_be_clickable(chat_locator))
                    text_area = self.driver.find_element_by_xpath(chat_text_area)
                    text_area.clear()
                    message = secrets.choice(DEFAULT_CHAT_MESSAGES)
                    if len(message.strip()) > 0:
                        text_area.send_keys(message)
                        self.web_driver_wait.until(ec.element_to_be_clickable(send_chat_locator))
                        send_text_area = self.driver.find_element_by_xpath(send_chat_text_area)
                        send_text_area.click()
                        logger.info('Message sent to {}: {}.'.format(profile_name, message))
                    else:
                        logger.warning('Empty messages cannot be sent.')
            except NoSuchElementException:
                logger.error(self.UPDATE_XPATH_STRING)
                logger.error('Skipping sending messages to matching profiles.')
        else:
            logger.warning('Cannot choose from an empty sequence, please fill the message list with some values.')

    def check_match_answered(self, profile_name):
        logger.info('Checking if matching profile {} has answered'.format(profile_name))

        # To check if there is an answer, the content of the chat is used to find out if the confirmation text of sent is present.
        # If the person has answered, that text will not appear since a heart will be in its place to like the answer.
        chat_body = self.driver.find_element_by_xpath('//div[@aria-label="{}"]'.format(ARIA_LABEL_CHAT))
        chat_text = chat_body.text
        last_line = chat_text.split('\n')[-1]

        if last_line.startswith(SENT_TEXT_CHAT) or last_line.startswith(READ_TEXT_CHAT):
            logger.info('The matching profile {} has not answered, skipping sending message.'.format(profile_name))
            return False
        else:
            logger.info('The matching profile {} has answered, sending message.'.format(profile_name))
            return True

    def collect_photos_matched_profiles(self, skip_animation=True):
        logger.info('Retrieving profile photos from matching profiles.')

        try:
            self.switch_to_tab(messages_tab, 'messages')
            list_locator = (By.XPATH, matched_profiles_list)
            self.web_driver_wait.until(ec.element_to_be_clickable(list_locator))
            match_list = self.driver.find_element_by_xpath(matched_profiles_list)
            # The list of matches is a <div> of <a> tags. The . at the beginning specifies to find all child nodes.
            profiles_list = match_list.find_elements_by_xpath('.//a')
            self.get_photos_matched_profiles(profiles_list, skip_animation)
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Skipping recovering photos from matching profiles.')
        except TimeoutException:
            logger.warning('Timeout exception when collecting photos from matching profiles, there could be a network problem.')

    def get_photos_matched_profiles(self, profiles_list, skip_animation):
        if len(profiles_list) > 0:
            try:
                # If you use this function without having previously used the auto_swipe function, you will get an error that the
                # xpaths cannot be found because the chat for the pressed match does not load until the tutorial animation finishes.
                if not skip_animation:
                    self.wait_end_animation(cardboard)

                for profile in profiles_list:
                    profile.click()
                    self.simulate_human_response_time()  # We need to allow time for photos to be loaded.
                    self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, matched_profile_name_path)))
                    profile_name = profile.find_element_by_xpath(matched_profile_name_path).text
                    profile_age = profile.find_element_by_xpath(matched_profile_age_path).text
                    logger.info('Retrieving profile photos for match: {}.'.format(profile_name))
                    array_of_buttons = self.driver.find_elements_by_xpath(matched_profile_photos_selector)
                    if len(array_of_buttons) > 0:  # The profile has more than one photo.
                        selector_of_photos = array_of_buttons[0]
                        photos_available = selector_of_photos.find_elements_by_xpath('.//button')
                        selector = matched_profile_photo_selector_button
                        selected_photo = matched_profile_photo_path
                        photos = self.loop_over_photos(photos_available, selector, selected_photo)
                        details = self.PHOTO_FOLDER_NAME.substitute(name=profile_name, age=profile_age, photos=len(photos))
                        for photo in photos:
                            self.simulate_human_response_time()
                            self.load_image_from_url(self.matched_folder, photo, details)
                    else:  # The profile has only one photo.
                        self.simulate_human_response_time()
                        photo_url = self.get_profile_photo(matched_profile_one_photo_path)
                        details = self.PHOTO_FOLDER_NAME.substitute(name=profile_name, age=profile_age, photos=1)
                        self.load_image_from_url(self.matched_folder, photo_url, details)
            except StaleElementReferenceException:
                logger.error('Element no longer attached to the DOM, not in the current frame context or the document has been refreshed.')
            except NoSuchElementException:
                logger.error(self.UPDATE_XPATH_STRING)
                logger.error('Skipping recovering photos from matching profiles.')
        else:
            logger.info('There are no matching profiles, deleting folder.')
            self.remove_photo_folder(self.matched_folder)

    def wait_end_animation(self, xpath):
        logger.info('Waiting for the tutorial animation to finish.')
        try:
            self.web_driver_wait.until(ec.element_to_be_clickable((By.XPATH, xpath)))
        except TimeoutException:
            logger.info('Search animation in progress, no profiles are shown.')

    # Deprecated: It seems that Tinder now checks to see if your account has access to the original photo, so this method no longer works
    # because trying to get the original photo produces an access denied error instead of getting the photo.
    def check_blurry_matches(self):
        logger.info('Checking photos of gold matches.')

        self.switch_to_tab(matches_tab, 'matches')
        try:
            group_locator = (By.XPATH, grouped_matches)
            self.web_driver_wait.until(ec.element_to_be_clickable(group_locator))
            group_list = self.driver.find_element_by_xpath(grouped_matches)
            group_list.click()

            # We have to wait for the blurry photos to load.
            self.simulate_human_response_time()

            blurry_locator = (By.XPATH, blurry_list)
            self.web_driver_wait.until(ec.element_to_be_clickable(blurry_locator))
            blurry_profiles_list = self.driver.find_element_by_xpath(blurry_list)
            blurry_profiles = blurry_profiles_list.find_elements_by_class_name(BLURRED_ITEM_CLASS)

            if len(blurry_profiles) > 0:
                self.get_focused_photos(blurry_profiles)
            else:
                logger.info('There are no matches available for you at this time.')
                self.remove_photo_folder(self.gold_matches_folder)
        except TimeoutException:
            logger.info('There are no matches available for you at this time.')
            self.remove_photo_folder(self.gold_matches_folder)
        except NoSuchElementException:
            logger.error(self.UPDATE_XPATH_STRING)
            logger.error('Skipping recovering photos from gold matches.')

    def get_focused_photos(self, blurry_profiles):
        logger.info('Retrieving photos of gold matches.')

        for blurry_profile in blurry_profiles:
            self.simulate_human_response_time()
            thumbnail_container = blurry_profile.find_elements_by_class_name(BLURRED_PHOTO_CLASS)
            if len(thumbnail_container) > 0:
                thumbnail = thumbnail_container[0]
                css_property = thumbnail.value_of_css_property('background-image')
                thumbnail_url = css_property.strip('url(\"').strip('\")')
                if not thumbnail_url.endswith(UNKNOWN_SUFFIX):
                    logger.info('Found thumbnail URL: {}'.format(thumbnail_url))
                    # Tinder has 2 sizes of photos, 640x640 and 640x800. If the thumbnail has a size of 84x84 the
                    # original size will be 640x640 and if the thumbnail is 84x106 the original size will be 640x800.
                    for thumbnail_size, original_size in THUMBNAIL_ORIGINAL_SIZE_MAPPING.items():
                        cleaned_size = thumbnail_size.replace('/', '').replace('_', '')
                        if thumbnail_size in thumbnail_url:
                            logger.info('Trying to get the original photo of thumbnail size: {}'.format(cleaned_size))
                            original_photo_url = thumbnail_url.replace(thumbnail_size, original_size)
                            result = self.load_image_from_url(self.gold_matches_folder, original_photo_url)
                            if result is not None:
                                break
                        else:
                            logger.warning('No original photo found for thumbnail size: {}.'.format(cleaned_size))
                else:
                    logger.info('There is a gold match without photo profile. Skipping.')
            else:
                logger.warning('Something went wrong when recovering the blurry photo.')

    def check_crontab_entry(self):
        logger.info('Checking Crontab for the next execution.')

        script_directory = pathlib.Path(__file__).parent.absolute()
        script_path = os.path.join(script_directory, 'crontab_script.sh')
        command_text = 'bash {}'.format(script_path)
        comment_text = CRONTAB_BOT_COMMENT

        self.remove_crontab_entry(comment_text)
        self.add_crontab_entry(command_text, comment_text)

    @staticmethod
    def remove_crontab_entry(comment_text=CRONTAB_BOT_COMMENT):
        user_crontab = CronTab(user=True)
        job = user_crontab.find_comment(comment_text)

        if job:
            user_crontab.remove(job)
            user_crontab.write()
            logger.info('Previous job entry in Crontab was removed.')
        else:
            logger.info('No previous job entry was found in Crontab.')

    def add_crontab_entry(self, command_text, comment_text):
        user_crontab = CronTab(user=True)
        job = user_crontab.new(command=command_text, comment=comment_text)

        # The bot will wait in 2 different ways:
        # 1 - If the bot closes because no more profiles are displayed, it will wait 1 hour to let Tinder refresh the profile list.
        # 2 - If the bot closes because it has reached the free matches limit, it will wait 12 hours and 5 minutes before it starts again.
        # Tinder has a cooldown time of 12 hours but I give 5 minutes of margin.
        if self.free_limit_reached:
            time_pattern = '5 */12 * * *'
        else:
            time_pattern = '0 * * * *'

        job.setall(time_pattern)

        if job.is_valid():
            logger.info('Adding new job entry in Crontab.')
            job.enable()
            user_crontab.write()
        else:
            logger.warning('Invalid Crontab job entry, check the syntax.The bot will not execute automatically.')

    def exit(self):
        logger.info('Closing the bot.')

        self.driver.quit()


if __name__ == "__main__":  # Execute only if run as a script
    bot = TinderBot()
    if bot.check_user_constants():
        bot.login()
        bot.close_permission_popups()
        bot.auto_swipe()
        bot.collect_photos_matched_profiles(skip_animation=True)
        bot.review_messages_from_matching_profiles(skip_animation=True)
        bot.remove_photo_folder(bot.temporary_folder)
        bot.check_crontab_entry()
        bot.exit()
