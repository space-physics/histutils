function oct = isoctave()

oct = exist('OCTAVE_VERSION', 'builtin') == 5;

end
