import cv2
import numpy as np
import os
from glob import glob
from os.path import join
import tarfile
import urllib

from matplotlib import pyplot as plt
import tensorflow as tf


# DeepLab 모델로 DeepLabModel 클래스 만듬
class DeepLabModel(object):
    INPUT_TENSOR_NAME = 'ImageTensor:0'
    OUTPUT_TENSOR_NAME = 'SemanticPredictions:0'
    INPUT_SIZE = 513
    FROZEN_GRAPH_NAME = 'frozen_inference_graph'

    # __init__()에서 모델 구조를 직접 구현하는 대신, tar file에서 읽어들인 그래프구조 graph_def를
    # tf.compat.v1.import_graph_def를 통해 불러들여 활용하게 됩니다.
    def __init__(self, tarball_path):
        self.graph = tf.Graph()
        graph_def = None
        tar_file = tarfile.open(tarball_path)
        for tar_info in tar_file.getmembers():
            if self.FROZEN_GRAPH_NAME in os.path.basename(tar_info.name):
                file_handle = tar_file.extractfile(tar_info)
                graph_def = tf.compat.v1.GraphDef.FromString(file_handle.read())
                break
        tar_file.close()

        with self.graph.as_default():
            tf.compat.v1.import_graph_def(graph_def, name='')

        self.sess = tf.compat.v1.Session(graph=self.graph)

    # 이미지를 전처리하여 Tensorflow 입력으로 사용 가능한 shape의 Numpy Array로 변환합니다.
    def preprocess(self, img_orig):
        height, width = img_orig.shape[:2]
        resize_ratio = 1.0 * self.INPUT_SIZE / max(width, height)
        target_size = (int(resize_ratio * width), int(resize_ratio * height))
        resized_image = cv2.resize(img_orig, target_size)
        resized_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        img_input = resized_rgb
        return img_input

    def run(self, image):
        img_input = self.preprocess(image)

        # Tensorflow V1에서는 model(input) 방식이 아니라 sess.run(feed_dict={input...}) 방식을 활용합니다.
        batch_seg_map = self.sess.run(
            self.OUTPUT_TENSOR_NAME,
            feed_dict={self.INPUT_TENSOR_NAME: [img_input]})

        seg_map = batch_seg_map[0]
        return cv2.cvtColor(img_input, cv2.COLOR_RGB2BGR), seg_map

def print_shape(img_path):
    img_orig = cv2.imread(img_path)
    print(img_orig.shape)
    return img_orig

def get_weight(img_path,segmap,imgbackground):
    # 사전에 학습된 가중치를 불러옴
    # define model and download & load pretrained weight
    _DOWNLOAD_URL_PREFIX = 'http://download.tensorflow.org/models/'

    model_dir = os.getenv('HOME') + '/aiffel/human_segmentation/models'
    tf.io.gfile.makedirs(model_dir)

    print('temp directory:', model_dir)

    download_path = os.path.join(model_dir, 'deeplab_model.tar.gz')
    if not os.path.exists(download_path):
        urllib.request.urlretrieve(_DOWNLOAD_URL_PREFIX + 'deeplabv3_mnv2_pascal_train_aug_2018_01_29.tar.gz',
                                   download_path)

    MODEL = DeepLabModel(download_path)
    print('model loaded successfully!')

    img_orig = print_shape(img_path)
    # 이미지를 네트워크에 입력
    img_resized, seg_map = MODEL.run(img_orig)
    print(img_orig.shape, img_resized.shape, seg_map.max())

    img_back_orig = print_shape(imgbackground)
    img_background_resized, seg_map2 = MODEL.run(img_back_orig)
    print(img_back_orig.shape, img_resized.shape, seg_map2.max())

    # 사람 영역만 검출
    img_show = img_resized.copy()
    seg_map = np.where(seg_map == segmap, segmap, 0)  # 예측 중 사람만 추출
    img_mask = seg_map * (255 / seg_map.max())  # 255 normalization
    img_mask = img_mask.astype(np.uint8)
    color_mask = cv2.applyColorMap(img_mask, cv2.COLORMAP_JET)
    img_show = cv2.addWeighted(img_show, 0.6, color_mask, 0.35, 0.0)
    plt.imshow(cv2.cvtColor(img_show, cv2.COLOR_BGR2RGB))
    plt.show()

    #img_show2 = img_back_orig.copy()
    seg_map2 = np.where(seg_map2 == segmap, segmap, 0)
    img_background = seg_map2 * (255 / seg_map2.max())
    img_background = img_background.astype(np.uint8)
    #img_show2 = cv2.addWeighted(img_show2, 0.6, color_mask, 0.35, 0.0)
    #plt.imshow(cv2.cvtColor(img_show2, cv2.COLOR_BGR2RGB))
    #plt.show()


    # 세그멘테이션 결과를 원래 크기로 복원
    img_mask_up = cv2.resize(img_mask, img_orig.shape[:2][::-1], interpolation=cv2.INTER_LINEAR)
    _, img_mask_up = cv2.threshold(img_mask_up, 128, 255, cv2.THRESH_BINARY)

    img_background_up = cv2.resize(img_background, img_back_orig.shape[:2][::-1], interpolation=cv2.INTER_LINEAR)
    _, img_background_up = cv2.threshold(img_background_up, 128, 255, cv2.THRESH_BINARY)


    #ax = plt.subplot(1, 2, 1)
    #plt.imshow(img_background_up, cmap=plt.cm.binary_r)
    #ax.set_title('Original Size Mask')

    #ax = plt.subplot(1, 2, 2)
    #plt.imshow(img_background, cmap=plt.cm.binary_r)
    #ax.set_title('DeepLab Model Mask')
    #plt.show()


    # 배경을 흐리게 하기 위해서 세그멘테이션 마스크를 이용해서 배경만 추출
    img_mask_color = cv2.cvtColor(img_mask_up, cv2.COLOR_GRAY2BGR)
    img_bg_mask = cv2.bitwise_not(img_mask_color)
    img_bg = cv2.bitwise_and(img_back_orig, img_bg_mask)
    img_bg_blur = cv2.blur(img_bg, (13, 13))
    #plt.imshow(img_bg_blur)
    #plt.show()

    # 흐린 배경과 원본 영상 합성
    img_concat = np.where(img_mask_color == 255, img_orig, img_bg_blur)
    plt.imshow(cv2.cvtColor(img_concat, cv2.COLOR_BGR2RGB))
    plt.show()


def main():

    img_path = os.getenv('HOME') + '/aiffel/human_segmentation/images/my_image.jpeg'
    img_background = os.getenv('HOME') + '/aiffel/human_segmentation/images/background.jpg'
    get_weight(img_path, 15, img_path)
    get_weight(img_path,15,img_background)

    img_path = os.getenv('HOME')+'/aiffel/human_segmentation/images/cat.jpeg'
    get_weight(img_path,8,img_path)

    img_path = os.getenv('HOME') + '/aiffel/human_segmentation/images/people3.jpg'
    get_weight(img_path, 15, img_path)

if __name__ == "__main__":
    main()