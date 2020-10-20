# -*- coding: utf-8 -*-
"""FaceRecognition.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1oAnc5l9ec923ufaEYPLJbqJ8XV5qd9Yi
"""

cd drive/My Drive/900Faces

!ls

!7z x dataset.7z

"""**SOME PROBLEMS WITH THE DATASET**

A few problems discovered in the dataset during testing:
1. 03MUCT_i429 and 03MUCT_i088 are the same person 
2. 05faces94_gotone is not a person, but a collection of other people in this dataset (05faces94_astefa, 05faces94_sbains and 10 others)

Delete 05faces94_gotone and 03MUCT_i0429 folders. 

SVC still classifies with an accuracy of over 99% using just two samples per person, even with these mistakes.

**PREPROCESSING THE DATASET**

This section takes a bulk dataset and divides it into a trainset and a testset based on the ratio of photos specified to use for test. If the dataset has been partitioned already, can proceed to train directly.
"""

import os, random
from tqdm import tqdm
from shutil import copyfile

def create_set_dictionary(directory):
	'''
	Returns a dictionary

	Keys are the names of people
	corresponding Values are the lists of relative paths to the images
	'''
	data = {}

	for folder in tqdm(os.listdir(directory)):
		label_name = folder
		photos_full_paths = []
	
		for photo in os.listdir(os.path.join(directory, folder)):
			photos_full_paths.append(os.path.join(directory, label_name, photo))
	
		data[label_name] = photos_full_paths
	return data

def makdir(path):
	if not os.path.isdir(path):
		os.makedirs(path)

def split_dataset(folder, label, testratio):
	'''
	Creates trainset and testset directories by randomly choosing the test set
	and using the rest for the train set

	Function supposed to be run only once for the same dataset
	'''
	all_images = os.listdir(os.path.join(folder, label))

	test_files = random.sample(all_images, int(testratio*len(all_images)))

	train_files = [file for file in all_images if file not in test_files]

	makdir(os.path.join(test_dir, label))
	makdir(os.path.join(train_dir, label))

	for image in test_files:
		copyfile(os.path.join(folder, label, image), os.path.join(test_dir, label, image))
  
	for image in train_files:
		copyfile(os.path.join(folder, label, image), os.path.join(train_dir, label, image))

folder = "dataset" # path to the bulk dataset
testratio = 0.35 # 35% of photos for each label will be used for test purpose i.e. 65% for training
everything = create_set_dictionary(folder)
print("created a dictionary of paths inside the dataset")

train_dir = "trainset" # train_dir and test_dir variables are required for split_dataset function
test_dir = "testset"

makdir(train_dir)
makdir(test_dir)
makdir("records") # directory to store record files CSV

print("partitioning the dataset into train and test")
for label in tqdm(everything):
    split_dataset(folder, label, testratio)

"""**FACE RECOGNITION**"""

! pip install face_recognition

import csv, json, cv2, os, face_recognition
from time import time, ctime, sleep
import numpy as np
from tqdm import tqdm

'''
Expects directory structure as follows:

trainset
  -->label1
    -->photo1.jpg
    -->photo2.jpg
  -->label2
    -->photo1.jpg
    etc

testset
  -->label1
    -->photo1.jpg
    -->photo2.jpg
  -->label2
    -->photo1.jpg
  etc
'''

class Pipeline:
    ALGORITHM = None
    def __init__(self, train_res, infer_res, train_dir, test_dir):
        self.RESIZE_DIM_TRAINING = train_res
        self.RESIZE_DIM_INFERENCE = infer_res

        self.train_dir = train_dir
        self.test_dir = test_dir
        self.train_dict = self.create_set_dictionary(self.train_dir)
        self.test_dict = self.create_set_dictionary(self.test_dir)

    def create_set_dictionary(self, directory):
        '''
        Returns a dictionary

        Keys are the names of people
        corresponding Values are the lists of relative paths to the images
        '''
        data = {}

        for folder in os.listdir(directory):
            label_name = folder
            photos_full_paths = []

            for photo in os.listdir(os.path.join(directory, folder)):
                photos_full_paths.append(os.path.join(directory, label_name, photo))

            data[label_name] = photos_full_paths

        return data

    def img_resize(self, img_array, resizeto):
        '''
        Resizes images preserving the aspect ration

        input: image's array and a single dimension for the resizing
        '''

        height, width = img_array.shape[:2]
        resize_h, resize_w = 0, 0

        if height > width:
            if height > resizeto:
                resize_h = resizeto
                resize_w = int(resize_h * width/height)
            else: return img_array
        else:
            if width >= resizeto:
                resize_w = resizeto
                resize_h = int(resize_w * height/width)
            else: return img_array

        new = cv2.resize(img_array, (resize_w, resize_h))

        # # to view the photos
        # plt.imshow(new, interpolation='nearest')
        # plt.show()

        return new

    def extract_encodings(self, data, no_of_samples, resize=True):
        '''
        Extracts the encodings of images fed through the dictionary prepared 
        using `create_set_dictionary`

        input: dictionary, no of samples to encode per label

        Returns encodings of images and labels which are in order
        '''
        face_encodings = []
        names = []

        for person in tqdm(data):
            train_samples = 0 # number of training samples whose face encodings have been extracted, just a counter

            for image in data[person]:
                # print(f"processing {image}")
                face = face_recognition.load_image_file(image)
                if resize: face = self.img_resize(face, self.RESIZE_DIM_TRAINING)

                face_bounding_boxes = face_recognition.face_locations(face)

                if len(face_bounding_boxes) == 1:
                    face_enc = face_recognition.face_encodings(face)[0]
                    face_encodings.append(face_enc)
                    names.append(person)
                    train_samples += 1

                    if train_samples >= no_of_samples: break # Make sure we don't take more than {training_samples} no of samples
                else:
                    print(image + " can't be used for training and has been skipped") # No face in the photo, or more than one

        return face_encodings, names
    
    def pipeline(self, low=3, high=4, resize=True, verbose=True): 
        # using (low=3, high=4) implies 3 samples per label by default
        # (low=2, high=5) implies go for three iterations with 2 samples, 3 samples, and 4 samples
        for i in range(low, high):
            print(f"USING {i} SAMPLE(s) PER LABEL")

            start = time()
   
            print("training in progress")
            sleep(0.2)
            self.train(i, resize=resize)

            train_time = time()-start
            print(f"time to encode + train: {train_time}")

            print("testing in progress")
            sleep(0.2)
            acc = self.test(resize=resize, verbose=verbose)

            time_taken = time()-start
            print(f"total time taken: {time_taken}")

            # Add to the records file
            self.keep(i, self.algo_spec, acc, train_time, time_taken)

    def keep(self, no_of_samples, algo_spec, accuracy, train_time, total_time):
        file = ctime()[:10]

        file_path = f"records/{file}.csv"

        if os.path.isfile(file_path):
            with open(f"records/{file}.csv", "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow([self.ALGORITHM, no_of_samples, self.RESIZE_DIM_TRAINING, self.RESIZE_DIM_INFERENCE, \
                    json.dumps(algo_spec,  ensure_ascii=False), accuracy, train_time, total_time])
        else:
            with open(f"records/{file}.csv", "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["algorithm", "no of samples", "train_resize_dim", "test_resize_dim", "algorithm specific", "accuracy", "train time", "total time"])
            self.keep(no_of_samples, algo_spec, accuracy, train_time, total_time)

class byDistance(Pipeline):
    def __init__(self, train_res, infer_res, train_dir, test_dir, distance_cutoff):
        super().__init__(train_res, infer_res, train_dir, test_dir)
        self.ALGORITHM = "distance"
        self.cutoff = distance_cutoff
        self.algo_spec = {"cutoff": distance_cutoff}

    def train(self, no_of_samples, resize=True):
        self.encodings, self.labels = self.extract_encodings(self.train_dict, no_of_samples, resize)

    def test(self, resize=True, verbose=True):
        correct_count = 0
        samples = 0

        for person in tqdm(self.test_dict):
            for image in self.test_dict[person]:
                try:
                    test_image = face_recognition.load_image_file(image)
                    if resize: test_image = self.img_resize(test_image, self.RESIZE_DIM_INFERENCE)

                    face_locations = face_recognition.face_locations(test_image)

                    if len(face_locations) > 0:
                        samples += 1
                        test_image_enc = face_recognition.face_encodings(test_image)[0]
                        face_distances = face_recognition.face_distance(self.encodings, test_image_enc)
                        min_distance = np.amin(face_distances)
                        
                        if min_distance < self.cutoff:
                            min_distances = np.full_like(face_distances, 1)

                            for x in np.where(face_distances < self.cutoff): min_distances[x] = face_distances[x]

                            min_index = np.where(min_distances == min_distance)[0][0]

                            pred_label = self.labels[min_index]

                            if person == pred_label:
                                # correct_text = "which is correct"
                                correct_count += 1
                            else:
                                correct_text = "which is incorrect"
                                if verbose: print(f"found {pred_label} in {image} (distance={min_distance}) {correct_text}")
                        else:
                            print(f"no match found for {image}")
                except:
                    print(f"file load error: {image}")
        accuracy = correct_count/samples * 100
        print(f"{accuracy}% correctly classified")

        return accuracy

class MLAlg(Pipeline):
    def __init__(self, algorithm, clf, algo_spec, train_res, infer_res, train_dir, test_dir):
        super().__init__(train_res, infer_res, train_dir, test_dir)
        self.ALGORITHM = algorithm
        self.clf = clf
        self.algo_spec = algo_spec

    def train(self, no_of_samples, resize=True):
        self.encodings, self.labels = self.extract_encodings(self.train_dict, no_of_samples, resize)
        self.clf.fit(self.encodings, self.labels)

    def test(self, resize=True, verbose=True):
        correct_count = 0
        samples = 0

        for person in tqdm(self.test_dict):
            for image in self.test_dict[person]:
                try:
                    test_image = face_recognition.load_image_file(image)
                    if resize: test_image = self.img_resize(test_image, self.RESIZE_DIM_INFERENCE)

                    face_locations = face_recognition.face_locations(test_image)

                    if len(face_locations) > 0:
                        samples += 1
                        test_image_enc = face_recognition.face_encodings(test_image)[0]

                        name = self.clf.predict([test_image_enc])

                        if person == name[0]:
                            # correct_text = "which is correct"
                            correct_count += 1
                        else:
                            correct_text = "which is incorrect"
                            if verbose: print(f"found {name[0]} in {image} {correct_text}")  
                except:
                    print(f"file load error: {image}")
                    
        accuracy = correct_count/samples * 100
        print(f"{accuracy}% correctly classified")

        return accuracy

trainset = "trainset"
testset = "testset"

# How to run (train and test) a (sklearn-type) classifier

# import the classifier: from sklearn import svm
# set up the classifier: clf = svm.SVC(gamma="scale")

# start an instance of our pipeline: 
# instance = MLAlg(`name`, clf, special properties of the classifier (as a dict), train resolution, test resolution, train directory, test directory)

# run the pipeline: instance.pipeline(low=2, high=5, verbose=True)
# or just train: instance.train(no of samples)

"""First train run is slower than successive runs."""

from sklearn import svm
# SVC
clf = svm.SVC(gamma='scale')
instance = MLAlg("svm", clf, {"gamma":"scale"}, 200, 400, trainset, testset)
instance.pipeline(low=2, high=5, verbose=True) # Set verbose=False to repress details about misclassifications

# Distance-based
cutoff = 0.6 # Distance cutoff (between 0 and 1) (higher is stricter)
instance = byDistance(200, 300, trainset, testset, cutoff)
instance.pipeline(low=2, high=5, verbose=True)