# Do not remove these lines describing copyright and use restrictions
# - Copyright 2008, 2015  James Carson and Rick Jacob, Pacific Northwest National Laboratory
# - james.carson@gmail.com and richard.jacob@pnnl.gov
# - Do not distribute original or modified versions without authors' permission
# - For public research use only; not for commercial use without authors' permission
# - Acknowledge use via reference http://dx.doi.org/10.1371/journal.pone.0006670


from Tkinter import *
import sys, os, glob, math
try:
	import ImageChops, Image, ImageFilter, ImageStat, ImageEnhance
except: 
	from PIL import ImageChops, Image, ImageFilter, ImageStat, ImageEnhance
from numpy import *
from copy import copy

try:
	import PngImagePlugin
	import TiffImagePlugin
	import BmpImagePlugin
	import JpegImagePlugin
except:
	print "One or more image plugins not found"

def d2int():
	class App:
		def __init__(self, master):
			frame=Frame(master)
			frame.pack()
			self.intro=Label(frame, text="Welcome to D2 Calculator version 0.2\nDeveloped for Battelle Corporate Office\nFor details on method, please refer to:\n  richard.jacob@pnnl.gov \n\nPlease direct questions to james.carson@gmail.com\nUnauthorized commercialization or distribution is strictly prohibited!")
			self.intro.pack(side=TOP)

			self.lblthrs1=Label(frame, text="\nNormalized Threshold")
			self.lblthrs1.pack(side=TOP)
			self.thrs1=Entry(frame)
			self.thrs1.pack(side=TOP)
			self.thrs1.insert(END, "225")

			self.lblthrs2=Label(frame, text="\nMinimum Particle Size")
			self.lblthrs2.pack(side=TOP)
			self.thrs2=Entry(frame)
			self.thrs2.pack(side=TOP)
			self.thrs2.insert(END, "100")

			self.lbldir1=Label(frame, text="\nInput Folder")
			self.lbldir1.pack(side=TOP)
			self.dir1=Entry(frame)
			self.dir1.pack(side=TOP)
			self.dir1.insert(END, "C:/D2_Lm/in/")

			self.lbldir2=Label(frame, text="\nOutput Folder")
			self.lbldir2.pack(side=TOP)
			self.dir2=Entry(frame)
			self.dir2.pack(side=TOP)
			self.dir2.insert(END, "C:/D2_Lm/out/")

			self.run_cd = Button(frame, text="Run!", command=self.run_cd)
			self.run_cd.pack(side=BOTTOM)

		def run_cd(self):
			try:
				t1=int(self.thrs1.get())
				t2=int(self.thrs2.get())
				dir1=self.dir1.get()
				dir2=self.dir2.get()
				status.set("Calculating, please wait")
			except ValueError:
				status.set("Input error, please try again")

			try:
				status.set( folder_D2(dir1,dir2,t1,t2) )
			except ValueError:
				status.set("Input error, please try again")

	class StatusBar(Frame):
	    def __init__(self, master):
        	Frame.__init__(self, master)
        	self.label = Label(self, bd=1, relief=SUNKEN, anchor=W)
        	self.label.pack(fill=X)
	    def set(self, format, *args):
        	self.label.config(text=format % args)
        	self.label.update_idletasks()
	    def clear(self):
        	self.label.config(text="")
        	self.label.update_idletasks()


	root=Tk()
	root.title("D2 Calculator")
	app=App(root)
	status = StatusBar(root)
	status.pack(side=BOTTOM, fill=X)
	status.set("Ready")
	root.mainloop()


def local_histogram_normalization(im):
	try:
		imr,img,imb=im.split()
	except:
		try:
			imr,img,imb,ima=im.split()
		except:
			img=im		# given image is not rgb
	w,h=img.size
	img.save('img.png')
	xwin=w/6+1
	ywin=h/5+1
	for x in range(0,w,xwin):
		for y in range(0,h,ywin):
			im_loc=img.crop((x,y,min(x+xwin,w),min(y+ywin,h)))
			local_max=ImageStat.Stat(im_loc).extrema[0][1]
			im_loc_norm=ImageChops.invert(im_loc.point(lambda i: local_max-i))
			img.paste(im_loc_norm,(x,y))
	return img


# thres is good from 215, 220, 225  starts to degrade above 235
def threshold(im,thres):
	w,h=im.size
	imt=im.point(lambda i: i-thres,"1")
	return ImageChops.darker(imt,Image.new("1",(w,h),1))

def detect_particles(im):
	w,h=im.size
	#im1=im.convert('1')	# makes image 0s and 255s.  Want to count the area of 255 particles.
	im1=im
	imb=Image.new('1',(w+2,h+2),0)
	imb.paste(im1,(1,1))	# add pixel thick boundary to image by pasting it into a black image 
	
	w,h=imb.size		# now includes boundaries

	ar=imb.getdata()
	#rar=resize(ar,(h,w))/255  # convert to array of 0s and 1s.  Will mark particles searched with number > 1
	rar=resize(ar,(h,w))  # convert to array of 0s and 1s.  Will mark particles searched with number > 1
	
	cur_x,cur_y=1,1		# starting point

	particle_size_list=[]

	while(cur_y<(h-1)):

		if rar[cur_y,cur_x]==1:
			# New particle found
			# Perform local search
			particle_number=len(particle_size_list)+2
			local_list=[]
			local_size=1
			local_list.append( (cur_y,cur_x) )
			rar[cur_y,cur_x]=particle_number
			
			while len(local_list)>0:
				# pop first point off list
				loc_y,loc_x=local_list.pop(0)

				# search all 4 adjacent points to see if they are unexplored part of particle	
				for loc in ( (loc_y-1,loc_x),(loc_y+1,loc_x),(loc_y,loc_x-1),(loc_y,loc_x+1) ):
					if rar[loc]==1:
						local_size+=1
						local_list.append(loc)
						rar[loc]=particle_number					
				
			particle_size_list.append(local_size)
			#print cur_x,cur_y,len(particle_size_list),local_size

		# advance global search pixel
		cur_x+=1
		if cur_x==w-1:
			cur_x=1
			cur_y+=1
		# end of while loop
				
	return particle_size_list

def prune_particles(psl,val):
	plist=copy(psl)
	x=0	
	while x<len(plist):
		dummy=1
		while ((dummy>-1)&(x<len(plist))):
			if plist[x]<val:
				dummy=plist.pop(x)
			else:
				dummy=-1
		x+=1
	return plist	

# adapted from http://www.baley.org/~doug/shootout/
def find_stats(plist):

	equivalent_diameters=[]
	for p in plist:
		equivalent_diameters.append(math.sqrt(4*p/pi))
	s=sum(equivalent_diameters)
	n=len(equivalent_diameters)
	m=s/float(n)
	avg_dev=0
	std_dev=0
	var=0
	skew=0
	kurtosis=0
	
	for d in equivalent_diameters:
		dev=d-m
		avg_dev+=abs(dev)
		var+=dev**2
		skew+=dev**3
		kurtosis+=dev**4
	avg_dev/=float(n)
	var/=float(n-1)
	std_dev=math.sqrt(var)
	
	if var>0.0:
		skew/=((n-1)*var*std_dev)
		kurtosis=kurtosis/(n*var*var)-3.0
	equivalent_diameters.sort()
	mid=n/2
	if (n%2)==0:
		med=(equivalent_diameters[mid] + equivalent_diameters[mid-1])/2
	else:
		med=equivalent_diameters[mid]

	D1=m*(1+(var/(m*m)))

	D2=m*(1+(var/(m*m+var)*(2+std_dev*skew/m)))
	
	return n,s,med,m,avg_dev,std_dev,var,skew,kurtosis,D1,D2

def folder_D2(dir_in,dir_out,t1,t2):

	try:
		os.chdir(dir_in)
		files=glob.glob("*")
		fs=dir_in.split("/")
		if len(fs[len(fs)-1])>0:
			report_filename=fs[len(fs)-1]+"_report.txt"
		else:
			report_filename=fs[len(fs)-2]+"_report.txt"
	except:
		return "Bad input directory"	

	try:
		os.chdir(dir_out)
	except:
		# Output directory does not exist.  Attempt to create.
		try:
			os.mkdir(dir_out)
		except:
			return "Bad output directory"

	try:	
		outf=open(report_filename,'w')
		outf.write("Report for "+dir_in+"\n")
		outf.write("ImageName\tNumberOfAirways\tTotalArea\tMedian\tMean\tAverageDeviation\tStandardDeviation\tVariance\tSkew\tKurtosis\tD1\tD2\n")
	except:
		return "Error creating output file"

	try:
		os.chdir(dir_in)
		psl_all=[]
		for f in files:
			try:
				imo=Image.open(f)
				pppp=imo.load()
				im_okay=1
			except:
				im_okay=0
			if im_okay:
				imn=local_histogram_normalization(imo)
				imn.save('temp.png')
				imt=threshold(imn,t1)
				psl=detect_particles(imt)
				psl_t2=prune_particles(psl,t2)
				stats=find_stats(psl_t2)
				outline=f+"\t%i"%stats[0]+"\t%i"%stats[1]+"\t%i"%stats[2]+"\t%i"%stats[3]+"\t%i"%stats[4]+"\t%i"%stats[5]+"\t%i"%stats[6]+"\t%.2f"%stats[7]+"\t%.2f"%stats[8]+"\t%i"%stats[9]+"\t%i"%stats[10]+"\n"
				outf.write(outline)
			psl_all=psl_all+psl_t2
		stats=find_stats(psl_all)
		outline="AllImages\t%i"%stats[0]+"\t%i"%stats[1]+"\t%i"%stats[2]+"\t%i"%stats[3]+"\t%i"%stats[4]+"\t%i"%stats[5]+"\t%i"%stats[6]+"\t%.2f"%stats[7]+"\t%.2f"%stats[8]+"\t%i"%stats[9]+"\t%i"%stats[10]+"\n"
		outf.write(outline)
		outf.close()
		return "D1 is "+str(int(stats[9]))+". D2 is "+str(int(stats[10]))
	except:
		outf.close()
		return "Error code 3"

# Run the program

if len(sys.argv)==2:
	if sys.argv[1]=="nogui":
		dir_in="C:/D2_Lm/"
		os.chdir(dir_in)
		folders=glob.glob("*")
		for fol in folders:
			print("Examining "+fol)
			if ((fol<>"test")&(fol<>"out")):
				print folder_D2(dir_in+fol,"C:/D2_Lm/out/",225,100)
	else:
		d2int()
else:
	d2int()			
