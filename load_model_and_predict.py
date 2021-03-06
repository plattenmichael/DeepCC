import tensorflow as tf
from tensorflow.python.saved_model import tag_constants
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class Predictor:

    def __init__(self, dl, image_path=None):
        '''

        :param model_path: Path to saved model
        :param image_path: Optional path to an image folder if you want to load custom images
        '''

        self.dl = dl
        self.image_path = image_path


    def load_and_predict_single_model(self, model_path):

        restored_graph = tf.Graph()
        with restored_graph.as_default():
            with tf.Session(graph=restored_graph) as sess:
                tf.saved_model.loader.load(
                    sess,
                    [tag_constants.SERVING],
                    model_path
                )

                # Grab hold of input/output nodes from the graph
                x_placeholder = restored_graph.get_tensor_by_name('x:0')
                y_placeholder = restored_graph.get_tensor_by_name('y:0')
                training_placeholder = restored_graph.get_tensor_by_name('training:0')
                predictions = restored_graph.get_tensor_by_name('predictions:0')

                # Get the testing dataset of the DataLoader
                if self.image_path is None:
                    _, dataset = self.dl.load_as_dataset()
                elif self.image_path is not None:
                    # Custom image path is defined, we want to load from that folder
                    dataset = self.dl.load_testing_set(custom_image_path=self.image_path)

                iterator = dataset.make_initializable_iterator()
                next_batch = iterator.get_next()

                mean_iou, update_op = tf.metrics.mean_iou(labels=y_placeholder, predictions=predictions, num_classes=2,
                                                          name='mean_iou')

                sess.run(iterator.initializer)
                validation_metrics_vars = tf.get_collection(tf.GraphKeys.LOCAL_VARIABLES,
                                                            scope='mean_iou')
                validation_metrics_init_op = tf.variables_initializer(var_list=validation_metrics_vars,
                                                                      name='validation_metrics_init')
                sess.run(validation_metrics_init_op)
                i = 0

                while True:
                    try:
                        image, label = sess.run(next_batch)
                        prediction, _ = sess.run([predictions, update_op], feed_dict={x_placeholder: image, y_placeholder: label, training_placeholder: False})

                        # Print segmentation result

                        plt.show()
                        pred_img = np.reshape(prediction, [256, 256])
                        label_img = np.reshape(label, [256, 256])
                        img = np.reshape(image, [256, 256])
                        plt.imshow(pred_img, cmap='Blues')
                        plt.imshow(label_img, alpha=0.3, cmap='Greys')
                        #plt.imshow(img, alpha=0.5, cmap='Reds')
                        plt.show()

                        i = i + 1
                    except tf.errors.OutOfRangeError:
                        break

                print('Metrics IOU:', sess.run(mean_iou))
                print(i)

    def load_and_predict_both_models(self, model_paths):

        predicted_imgs = []
        images = []

        for model_path in model_paths:
            model_predictions = []
            restored_graph = tf.Graph()
            with restored_graph.as_default():
                with tf.Session(graph=restored_graph) as sess:
                    tf.saved_model.loader.load(
                        sess,
                        [tag_constants.SERVING],
                        model_path
                    )

                    # Grab hold of input/output nodes from the graph
                    x_placeholder = restored_graph.get_tensor_by_name('x:0')
                    training_placeholder = restored_graph.get_tensor_by_name('training:0')
                    predictions = restored_graph.get_tensor_by_name('predictions:0')

                    # Get the testing dataset of the DataLoader
                    if self.image_path is None:
                        _, dataset = self.dl.load_as_dataset()
                    elif self.image_path is not None:
                        # Custom image path is defined, we want to load from that folder
                        image_names, dataset = self.dl.load_images(custom_image_path=self.image_path)

                    print(image_names)

                    iterator = dataset.make_initializable_iterator()
                    next_batch = iterator.get_next()

                    sess.run(iterator.initializer)
                    i = 0

                    while True:
                        try:
                            image = sess.run(next_batch)
                            prediction = sess.run([predictions],
                                                     feed_dict={x_placeholder: image, training_placeholder: False})
                            pred_img = np.reshape(prediction, [256, 256])
                            img = np.reshape(image, [256, 256])

                            model_predictions.append(pred_img)
                            images.append(img)

                            i = i + 1
                        except tf.errors.OutOfRangeError:
                            break

            predicted_imgs.append(model_predictions)

        result_df = pd.DataFrame(columns=['File', 'Fraction'])
        

        print(f'Saving files and writing results...')
        file = open(self.image_path[:-6] + 'results.txt', 'w')
        for cc, brain, img, name in zip(predicted_imgs[0], predicted_imgs[1], images, image_names):
            # Plot prediction overlayed image
            plt.figure()
            plt.imshow(cc + brain, cmap='Blues')
            plt.imshow(img, alpha=0.3, cmap='Reds')
            print(self.image_path[:-6] + name + '_seg' + '.jpeg')
            plt.imsave(self.image_path[:-6] + name + '_seg' + '.jpeg', cc + brain)
            plt.show()

            # Get fraction and write to results.txt
            frac = float(np.count_nonzero(cc)) / float(np.count_nonzero(brain))
            file.write(self.image_path[:-6] + name + '_seg: ' + str(frac) + '\n')
            
            result_df.loc[len(result_df)] = [name, frac]
            

        result_df.to_csv(self.image_path[:-6] + 'results.csv')
        file.close()
        print('Done!')


