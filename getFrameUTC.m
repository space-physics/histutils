function [firstUTC, lastUTC, reqUTC] = getFrameUTC(BigFN,ReqFrameInd,BytesPerImage,nHeadBytes)
% Michael Hirsch
% summing up scattered functions from 2011 to 2014
% this UTC timing is NOT guaranteed, that's what we're working to verify!
% this method bases UTC time on the knowledge of the first frame UTC time from
% NMEA, and constant frames/sec based on XML configuration file
%
% simplest usage: getFrameUTC(BigFN) tells you start, first, last UTC time ESTIMATES
% BigFN is the .DMCdata file name

if nargin<1 || isempty(BigFN), error('Currently you must specify .DMCdata filename'), end
if nargin<2, ReqFrameInd = []; end
if nargin<3, BytesPerImage = 512*512*16/8; end
if nargin<4, nHeadBytes = 4; end
reqUTC = []; %in case not used

rawFrameRate = 'auto';
startUTC = 'auto';
spd = 86400; %seconds/day

%% examine frame indices
[firstRawIndex, lastRawIndex, ReqRawInd] = getRawInd(BigFN,BytesPerImage,nHeadBytes,ReqFrameInd);
%% estimate frame timing
[rawFrameRate,startUTC] = DMCtimeparams(BigFN,rawFrameRate,startUTC);
%% use estimated parameters to estimate timing for other frames
firstUTC = (startUTC*spd + (firstRawIndex - 1) / rawFrameRate)/spd;
lastUTC = (startUTC*spd + (lastRawIndex - 1) / rawFrameRate)/spd; 
%% print
display(['first frame UTC estimate: ',datestr(firstUTC)])
display(['last frame UTC estimate: ',datestr(lastUTC)])
%% cleanup
if ~nargout, clear, end
end %function