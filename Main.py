from PIL import Image, ImageDraw
import os 
import random
import numpy as np
import multiprocessing

img_to_recreate = r"D:\Yohann\Photos\Sauvegarde_telephone\IMG-20210129-WA0010.jpg" 
folder_to_images = r"D:\Yohann\Photos\Sauvegarde_telephone"

def make_mosaic_picture(img_to_recreate : str, imgs_folder : str, img_save_path=None, nb_imgs_to_pick=500, color_acc=1, resolution=0.5, color_treshold = 5) -> None:

     """
     Function that create a mosaic of an image from different images
     
     the inputs are:
     
     img_to_recreate - the image to redo as a mosaic

     imgs_folder - the path to the images to pick from to make the mosaic

     img_save_path - the path that the image is saved by default None

     nb_imgs_to_pick - the number of image to pick from the imgs_folder for speed concern

     color_acc - the accuracy of the image average color by default 1 (all pixels checked)

     resolution - the resolution of the wanted output images between 0-1 (percentage) by default 0.2

     color_treshold - the color difference where we are considering the tile img to fir enough and stopping searching for more by default 10
     """
     
     # load the image
     with Image.open(img_to_recreate) as loaded_img:

          goal_img = loaded_img.copy()

     goal_img = goal_img.transpose(Image.ROTATE_90)
     img_size = goal_img.size

     # set number of rows and colomns
     x_res = img_size[0]*resolution # the number of rows
     y_res = img_size[1]*resolution # the number columns

     #size of each mosaic tile
     x_size = int(img_size[0]/x_res)+1
     y_size = int(img_size[1]/y_res)+1
     tile_size = x_size, y_size

     # offset to get the mid pixel color (ands not the top left corner pixel val)
     x_off = int(x_size/2)
     y_off = int(y_size/2)

     # set the pixel colors to match
     colors_to_match = []
     for x in range(0, img_size[0] - x_off, x_size):
          for y in range(0, img_size[1] - y_off, y_size):

               colors_to_match.append(((x, y), goal_img.getpixel((x + x_off, y + y_off))))
          
     # the list containing the average color of each sample picture
     img_data = []

     #filtering out non images files and shuffling the names
     images_names = [name for name in os.listdir(imgs_folder) if name.endswith(("jpg", "png", "jpeg"))]
     random.shuffle(images_names)

     #get the average rgb color of each image
     for i, name in enumerate(images_names[0 : nb_imgs_to_pick]):
          print(f"images color analysis. {i/nb_imgs_to_pick:.2%} from {nb_imgs_to_pick}")
          img_data.append((name, get_avg_color(os.path.join(imgs_folder, name), tile_size, color_acc)))
     print("images color analyzed.")

     print("picking pictures")

     #splitting the work into 4 chunks
     processes = []
     chunks = []
     split = 4
     chunk_size = len(colors_to_match)/split
     for i in range(split):
          chunks.append(colors_to_match[int(i*chunk_size):int((i+1)*chunk_size)])

     # processing per chunk
     for i, chunk_colors_to_match in enumerate(chunks):
          
          args = [imgs_folder, color_treshold, tile_size, chunk_colors_to_match, img_data, img_size, i]
          p = multiprocessing.Process(target=draw_tile, args=args)
          p.start()
          processes.append(p)

     for process in processes:
          process.join()   

     # merging all the chunks
     merge_quarters(Image.new("RGB", img_size), f"output.png") 

     #removing the non necessary quarters
     for i in range(4):
          if os.path.exists(f"output_{i}.png"):
               os.remove(f"output_{i}.png")

def draw_tile(imgs_folder, color_treshold, tile_size, colors_to_match, img_data, img_size, chunk_num):
    
    #the output image initialisation
     output_img = Image.new("RGB", img_size)

     #finding the best match
     for i, (pos, wanted_color) in enumerate(colors_to_match):
          
          if i%(len(colors_to_match)//50) == 0:
               print(f"picking pictures {i/len(colors_to_match):.2%} from {len(colors_to_match)}")
          best_match = "", 100000
          for img, color in img_data:
                         # get the color
               color_difference = calc_color_difference(wanted_color, color)

                         # keeping the best match
               if color_difference < best_match[1]:
                    best_match = img, color_difference

               if color_difference <= color_treshold:
                    break

                    # drawing the choosen img to the output image
          img_tile = Image.open(os.path.join(imgs_folder, best_match[0]))
          img_tile = img_tile.resize(tile_size)
          output_img.paste(img_tile, pos)
          
          output_img.save(f"output_{chunk_num}.png")
               
def calc_color_difference(wanted_color, color):
    r1, g1, b1 = color
    r2, g2, b2 = wanted_color

    d =  ((r2-r1)*0.30)**2
    d += ((g2-g1)*0.59)**2
    d += ((b2-b1)*0.11)**2
    return d

def get_avg_color(img_path : str, tile_size : tuple, color_acc : float):
     
     with Image.open(img_path) as img:

          img = img.resize(tile_size)

          avg_color_per_row = np.average(img, axis=0)
          try:
               r, g, b = np.average(avg_color_per_row, axis=0)
          except ValueError:
               r, g, b = 255//2, 255//2, 255//2

     return r, g, b

def merge_quarters(main_output_img, img_save_path):
     
     for i in range(4):
          quarter = Image.open(f"output_{i}.png")
          mask = Image.new("L", quarter.size, 0)
          draw = ImageDraw.Draw(mask)
          top_left = int((i)*(quarter.size[0])/4), 0
          right_bottom = int((i+1)*(quarter.size[0])/4), quarter.size[1]
          draw.rectangle((top_left, right_bottom), fill=255)

          main_output_img = Image.composite(quarter, main_output_img, mask)
          # main_output_img.show()

     #saving the modified img
     main_output_img.save(img_save_path)


if __name__ == "__main__":

     make_mosaic_picture(img_to_recreate, folder_to_images,
      img_save_path="output.png",
      nb_imgs_to_pick=500,
      resolution=0.07,
      color_treshold=30)