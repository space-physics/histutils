% [data, rawFrameInd,tUTC] = rawDMCreader()
%
% reads uint16 raw data files from DMC
% Tested with Octave 4.0 & Matlab R2014a
%  Dec 2011 / Mar 2012 / Mar 2014
%
% requires: getRawInd.m (custom written script)
%
% INPUTS:
% BigFN: huge .DMCdata filename to read
% xPix: # of x-pixels in sensor {512}
% yPix: # of y-pixels in sensor {512}
% rcbin: row,col binning factor of CCD [1,1]
% frameind: Frame numbers to extract from file -- this is NOT raw frame numbers,
% but rather 1-indexed from start of file
% playmovie: if ~= 0, play with pause moviePlay seconds
% clim: for imagesc, sets the upper and lower contrast. E.g. [1000, 1200]
% rawframerate: {'auto'} get from XML file (recommended) or manually specify
% startutc: {'auto'} get from NMEA file (recommended) or manually specify as  "datenum"
%
% OUTPUTS:
% data: uint16 16-bit data, sorted into frames (view with imagesc)
% rawFrameInd: int64 camera index since acquisition start (used to obtain UTC time of
% frame based on GPS)
% tUTC: estimated UTC time of frame -- unverified
%
% Examples:
%
% meteor example  (playing first 100 frames of video):
% [data,~,tUT] = rawDMCreader('/cygdrive/d/2014-03-30/2014-03-30T10-46-CamSer7196.DMCdata','framereq',1:100,'clim',[1000,2000],'rawframerate','auto','startutc','auto');
%
% meteor example (extracting first 1000 frames of video, then saving to .mat):
% [data,~,tUT] = rawDMCreader('/cygdrive/d/2014-03-30/2014-03-30T10-46-CamSer7196.DMCdata','framereq',1:1000,'rawframerate','auto','startutc','auto');
%
%------------
% flintmax('double') is 2^53 (biggest integer value we can hold in a
% double float variable in Matlab on a 64-bit Operating System)

function [data, rawFrameInd, tUTC]=rawDMCreader(bigfn,varargin)

p = inputParser;
addParamValue(p,'rowcol',[512,512])
addParamValue(p,'rcbin',[1,1])
addParamValue(p,'framereq',[])
addParamValue(p,'playmovie',[])
addParamValue(p,'clim',[])
addParamValue(p,'rawframerate',[])
addParamValue(p,'startutc',[])
addParamValue(p,'verbose',false) %#ok<*NVREPL>
parse(p,varargin{:})
U = p.Results;

if isstruct(U.playmovie)
    try
        playmovie.fps = U.playmovie.fps;
        playmovie.clim = U.playmovie.clim;
    catch
        warning('i didn''t understand your playback command')
        playmovie.fps = 10;
        playmovie.clim = [];
    end
elseif ~isempty(U.playmovie)
    playmovie.fps = U.playmovie;
    playmovie.clim = U.clim;
else
    playmovie = [];
end
%%
[rawFrameRate,startUTC] = DMCtimeparams(bigfn,U.rawframerate,U.startutc);
%% setup data parameters
% based on settings from .xml file (these stay pretty constant)
SuperX = U.rowcol(2)/U.rcbin(2);
SuperY = U.rowcol(1)/U.rcbin(1);
bpp = 16; %bits per pixel
nHeadBytes = 4; %bytes per header frame (32 bits for CCD .DMCdata)
nHeader = nHeadBytes/2; % one 16-bit word = 2 bytes
dFormat = 'uint16=>uint16';  %for Andor CCD
PixelsPerImage= SuperX * SuperY;
BytesPerImage = PixelsPerImage*bpp/8;
BytesPerFrame = BytesPerImage + nHeadBytes;

% get file size
fileInfo= dir(bigfn);
if isempty(fileInfo), error(['file does not exist: ',bigfn]), end
fileSizeBytes = fileInfo.bytes;

assert(fileSizeBytes >= BytesPerImage, ['File size ',int2str(fileSizeBytes),' is smaller than a single image frame!'])

nFrame = fileSizeBytes / BytesPerFrame; % by inspection
 %there should be no partial frames
if rem(nFrame,1) ~= 0
    warning(['Not reading file correctly, bytesPerFrame: ',int2str(BytesPerFrame)])
end

%% get "raw" frame numbers -- that Camera FPGA tags each frame with
% this raw frame is critical to knowing what time an image was taken, which
% is critical for the usability of this data in light of other sensors
% (radar, optical)
[firstRawInd, lastRawInd] = getRawInd(bigfn,BytesPerImage,nHeadBytes);
if U.verbose
    display([int2str(nFrame),' frames in file ', bigfn])
    display(['   file size in Bytes: ',sprintf('%ld',fileSizeBytes)])
    display(['first / last raw frame # ',int2str(firstRawInd),' / ',...
             int2str(lastRawInd)])
end
% if no requested frames were specified, read all frames. Otherwise, just
% return the requested frames
if isempty(U.framereq)
  FrameInd = 1:nFrame;
else
  FrameInd = U.framereq;
end
badReqInd = FrameInd > nFrame | FrameInd<1;

% check if we requested frames beyond what the BigFN contains
if any(badReqInd)
    warning(['You have requested Frames ',int2str(FrameInd(badReqInd)),', outside BigFN'])
end

%excise bad requests
FrameInd(badReqInd) = [];
% more parameters
nFrameExtract = length(FrameInd); %to preallocate properly
assert(nFrameExtract>0,'No frames requested were available in this file.')
nBytesExtract = nFrameExtract*BytesPerFrame;

display(['Extracting ',int2str(nBytesExtract),' bytes from frame ',int2str(FrameInd(1)),' to ',int2str(FrameInd(end))])

if nBytesExtract > 1e9
    warning(['This will require ',num2str(nBytesExtract/1e9,'%0.1f'),' Gigabytes of RAM.'])
end
%% preallocate
% note: Matlab's default data type is "double float", which takes 64-bits
% per number. That can use up all the RAM of your PC. The data is only
% 16-bit, so to load bigger files, I keep the data 16-bit.
% In analysis programs, we might convert the data frame-by-frame to double
% or single float as we stream the data through an algorithm.
% That's because many Matlab functions will crash or give unexpected
% results with integers (or single float!)
data = zeros(SuperY,SuperX,nFrameExtract,'uint16');
% I created a custom header, but I needed 32-bit numbers. So I stick two
% 16-bit numbers together when writing the data--Matlab needs to unstick
% and restick this number into a 32-bit integer again.
% then I store as int64 in case we want to do numerical operations --
% uint's can lead to unexpected results!
rawFrameInd = zeros(nFrameExtract,1,'int64');
if ~isempty(rawFrameRate)
    tUTC = nan(nFrameExtract,1,'double');
else
    tUTC = [];
end
%% read data
fid = fopen(bigfn,'r');
assert(fid>0, ['error opening ',bigfn])
jFrm = 0;
tic %in case of remote file system, give user sense of progress
disp('starting file read')
Toc=toc;
for iFrame = FrameInd

    jFrm = jFrm + 1; %used for indexing memory

    currByte = (iFrame - 1) * BytesPerFrame; %start at beginning of frame

    % advance to start of frame in bytes
    fsErr = fseek(fid,currByte,'bof');
    if fsErr
        error(['Could not seek to byte ',currByte,', request ',int2str(jFrm)])
    end

    %read data
    %we transpose because Labview writes ROW MAJOR and Matlab is COLUMN MAJOR
    data(:,:,jFrm) = transpose(fread(fid,[SuperY,SuperX],dFormat,0,'l')); %first read the image
    metadata = fread(fid,nHeader,dFormat,0,'l'); % we have to typecast this

    %stick two 16-bit numbers together again to make the actual 32-bit raw
    %frame index
    rawFrameInd(jFrm) = int64( typecast( [metadata(2), metadata(1)] ,'uint32') );
    if ~isempty(rawFrameRate)
        tUTC(jFrm) = U.startutc + ( rawFrameInd(jFrm) - 1 )/rawFrameRate /86400;
    end

    %progress for slow drives/connections
    if ~mod(jFrm,5) && toc-Toc>2
        Toc=toc;
        fprintf([num2str(jFrm/nFrameExtract*100,'%.1f'),'%%.. '])
    end

end %for

fclose(fid);
%% play movie, if user chooses
doPlayMovie(data,SuperY,SuperX,nFrameExtract,playmovie,rawFrameInd,tUTC)
%% cleanup
if ~nargout, clear, end
end %function

function doPlayMovie(data,nRow,nCol,nFrameExtract,playmovie,rawFrameInd,tUTC)
if isempty(playmovie)
    return
elseif isstruct(playmovie)
    pbpause = 1/playmovie.fps;
    Clim = playmovie.clim;
end
%% setup plot
    h.f = figure(1); clf(1)
    h.ax = axes('parent',h.f);
    switch isempty(Clim)
        case false, h.im = imagesc(zeros(nRow,nCol,'uint16'),Clim);
        case true,  h.im = imagesc(zeros(nRow,nCol,'uint16'));
    end %switch
   %flip the picture back upright.  Different programs have different ideas
   %about what corner of the image is the origin. Or whether to start indexing at (0,0) or (1,1).
    set(h.ax,'ydir','normal')
    % just some labels
    h.t = title(h.ax,'');
    colormap(h.ax,'gray')
    h.cb = colorbar('peer',h.ax);
    ylabel(h.cb,'Data Numbers')
    xlabel(h.ax,'x-pixels')
    ylabel(h.ax,'y-pixels')
%% do the plotting
% setting Cdata like this is much, MUCH faster than repeatedly calling
% imagesc() !
try
    for iFrame = 1:nFrameExtract
     set(h.im,'cdata',single(data(:,:,iFrame))) %convert to single just as displaying
     titlestring = ['Raw # ',int2str(rawFrameInd(iFrame)),...
           '  Relative # ',int2str(iFrame)];
     if ~isempty(tUTC)
         titlestring = [titlestring,'  time: ',datestr(tUTC(iFrame),'yyyy-mm-ddTHH:MM:SS.FFF'),' UTC']; %#ok<AGROW>
     end

     set(h.t,'String',titlestring)
     pause(pbpause)
    end
catch ME
    display(iFrame)
    try
        display(tUTC(iFrame))
        display(rawFrameInd(iFrame))
    end
    rethrow(ME)
end
%% cleanup
if nargout==0, clear, end
end %function
