# -*- coding: utf-8 -*-
try:
    import os.path
    import pathlib
    import sys

    import cv2
    import dlib
    from logger import logger
    import numpy as np
    from keras.applications.resnet50 import ResNet50
    from keras.backend import clear_session
    from keras.layers import Dense
    from keras.models import Sequential

    from resources.constants import TEMP_FOLDER
except ModuleNotFoundError:
    print('Something went wrong while importing dependencies. Please, check the requirements file.')
    sys.exit(1)

parent_path = os.path.dirname(os.path.abspath(__file__))

model_path = os.path.join(parent_path, 'beauty', 'model_human_face_detector.dat')
cnn_face_detector = dlib.cnn_face_detection_model_v1(model_path)

resnet = ResNet50(include_top=False, pooling='avg')
model = Sequential()
model.add(resnet)
model.add(Dense(5, activation='softmax'))
model.layers[0].trainable = False

weights_path = os.path.join(parent_path, 'beauty', 'model-ldl-resnet.h5')
model.load_weights(weights_path)

samples_folder = os.path.join(parent_path, 'beauty', 'samples')
output_folder = os.path.join(parent_path, TEMP_FOLDER, 'output')


def score_mapping(model_score):
    logger.info('Calculating the score.')
    mapping_score = 0

    if model_score <= 1.9:
        mapping_score = ((4 - 2.5) / (1.9 - 1.0)) * (model_score - 1.0) + 2.5
    elif model_score <= 2.8:
        mapping_score = ((5.5 - 4) / (2.8 - 1.9)) * (model_score - 1.9) + 4
    elif model_score <= 3.4:
        mapping_score = ((6.5 - 5.5) / (3.4 - 2.8)) * (model_score - 2.8) + 5.5
    elif model_score <= 4:
        mapping_score = ((8 - 6.5) / (4 - 3.4)) * (model_score - 3.4) + 6.5
    elif model_score < 5:
        mapping_score = ((9 - 8) / (5 - 4)) * (model_score - 4) + 8

    return mapping_score


def beauty_predict(path, details, image, show_result=False):
    logger.info('Predicting beauty. This process could take a while, be patient.'.format(image))
    punctuations = []

    image_path = os.path.join(path, details, image)
    image_matrix = cv2.imread(image_path)

    if image_matrix is not None:
        if image_matrix.shape[0] > 1280:
            new_shape = (1280, image_matrix.shape[1] * 1280 / image_matrix.shape[0])
        elif image_matrix.shape[1] > 1280:
            new_shape = (image_matrix.shape[0] * 1280 / image_matrix.shape[1], 1280)
        elif image_matrix.shape[0] < 640 or image_matrix.shape[1] < 640:
            new_shape = (image_matrix.shape[0] * 2, image_matrix.shape[1] * 2)
        else:
            new_shape = image_matrix.shape[0:2]

        resized_image_size = (int(new_shape[1]), int(new_shape[0]))
        resized_image = cv2.resize(image_matrix, resized_image_size)
        detected_faces = cnn_face_detector(resized_image, 0)

        if len(detected_faces) > 0:
            # The scores of the faces are stored from right to left order of their appearance in the photo.
            for face in detected_faces:
                values = [face.rect.left(), face.rect.top(), face.rect.right(), face.rect.bottom()]
                cropped_face_image = resized_image[values[1]:values[3], values[0]:values[2], :]
                output_image_size = (224, 224)
                try:
                    resized_face_image = cv2.resize(cropped_face_image, output_image_size)
                    normed_image = np.array([(resized_face_image - 127.5) / 127.5])

                    predictions = model.predict(normed_image)
                    ld_list = predictions[0]
                    output_value = 1 * ld_list[0] + 2 * ld_list[1] + 3 * ld_list[2] + 4 * ld_list[3] + 5 * ld_list[4]

                    punctuation = score_mapping(output_value)
                    punctuations.append(punctuation)
                    logger.info('Score for photo {}: {:.2f}'.format(image, punctuation))

                    if show_result:
                        draw_result(values, resized_image, punctuation)
                except cv2.error:
                    logger.error('OpenCV cannot resize the image {}, it can have a partial face.'.format(image_path))
                    break
                except ValueError:
                    logger.error('Aborting the process, the chart data from the previous session could not be deleted.')
                    clear_session()

            if show_result:
                generate_output_result(details, image, resized_image)
        else:
            # If the face in the photo is too small because it is far the predictor cannot detect it.
            logger.warning('Cannot calculate beauty score. The predictor could not detect the face in the photo.')
    else:
        logger.warning('Cannot read photo {} for processing. Invalid path or format.'.format(image_path))

    clear_session()

    return punctuations


# Show in a copy of the photo the detected faces and their respective score.
def draw_result(values, resized_image, punctuation):
    # Draw the rectangle
    vertex = (values[0], values[1])
    opposite_vertex = (values[2], values[3])
    rectangle_color = (0, 255, 0)  # Green
    rectangle_thickness = 3
    cv2.rectangle(resized_image, vertex, opposite_vertex, rectangle_color, rectangle_thickness)
    # Draw the score
    text = str('%.2f' % punctuation)
    text_corner = (values[0], values[3])
    text_color = (0, 0, 255)  # Red
    text_font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    text_thickness = 2
    cv2.putText(resized_image, text, text_corner, text_font, font_scale, text_color, text_thickness)


# Generates a copy of the photo with the detected faces and their respective score.
def generate_output_result(details, image, resized_image):
    logger.info('Generating output image with the results.')
    result_folder = os.path.join(output_folder, details)
    pathlib.Path(result_folder).mkdir(parents=True, exist_ok=True)
    detailed_image = os.path.join(result_folder, image)
    cv2.imwrite(detailed_image, resized_image)
