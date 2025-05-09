# MakerStop Design Decisions

The purpose of this page is to communicate my intentions through my design decisions. This includes the aspects of the project I consider most important, and the reasoning behind those priorities. It’s here to give context to current and future contributors, customers, or anyone digging into the project.

## Overview

MakerStop is a modular, 3D-printable automatic length stop system aimed at small fabrication shops, hobbyists, and maker spaces. It’s designed to be low-cost, highly customizable, and easy to assemble or maintain. The project balances printability, mechanical reliability, and accessibility.

**Key goals:**
- Must be adjustable in length to suit different applications
- Have an easy to use touch screen interface
- Cut list functionality 
- Needs to be light weight and compact enough to transport and ship
- Needs to be accurate and reliable


## Linear Motion

Linear motion is central to MakerStop’s function. Here's how I approached it:

- **Belt-Driven System:** I chose a GT3 timing belt as it is affordable, accurate and easy to source. A belt driven system allows for customizable length of motion. 
  
- **Linear Rails** The original prototype used linear rails and bearings as i had them left over from a CNC Build. While this is a great option, linear rails and bearings are expensive, heavy and difficult to source locally. 

I then worked on an MPCNC style carriage that used internally placed 15x5x5 Bearings. Another great option but it made for large complecated prints. 

I then took the Elon approach and began to question weather bearings were even necessary. In short, for this application, they aren't. I opted for 16mm round aluminium tube for the linear rails. The carriage hugs the rails with very little friction and allows for the affordability and modularity set out in the Goals section above. 

- **User Interface** It is tempting to build a mobile application to allow users to bring their own device but the decision was made to keep to the raspberry pi and touch screen interface to keep the user experience consistent and maintain a certain level of simplicity. 


**Firmware** FLUIDNC is a robust cnc firmware for ESP32 base controllers and works perfectly for this application. No need to reinvent the wheel. 

**Controller** Currently prototyping a custom controller design featuring ESP32 module and TB6600 stepper driver on the same board. It will also have a 5v rail to power the raspberry pi zero 2 and touch screen. Combining everything onto a single board will greatly reduce the space required in the touch screen enclosure, simplify the BOM and reduce the over all bom cost and assembly time. 