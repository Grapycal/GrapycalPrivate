from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from grapycal_audio import GrapycalAudio

from grapycal import Node, ButtonControl, to_numpy
from objectsync.sobject import SObjectSerialized
from .utils import byteFIFO
import pyaudio

class AudioOuputNode(Node):
    '''
    Play audio samples in the host machine.
    Send samples to the 'samples' port to play them. Accepts numpy arrays, torch tensors and python lists.
    Range of the samples should be between -1 and 1.
    '''
    ext: 'GrapycalAudio'
    category = 'audio/output'

    def build_node(self):
        self.samples_port = self.add_in_port('samples')
        self.reset_port = self.add_in_port('reset',control_type=ButtonControl)
        self.gain_control = self.add_text_control(name='gain',label='Gain', text='0.2')
        self.delay_control = self.add_text_control(name='delay',label='Delay', text='',readonly=True)
        self.label.set('Audio Output')

    def init_node(self):
        self.playing = False
        self.stream = None
        if self.is_preview.get():
            return
        self.buffer = byteFIFO()
        self.p = pyaudio.PyAudio()

        self.delay_update_i = 0

    def start_stream(self):
        print('Stream started')
        self.stream =  self.p.open(format=pyaudio.paFloat32,
            channels=1,
            rate=44100,
            output=True,
            stream_callback=self.callback,
            frames_per_buffer=self.ext.chunk_size)
        self.stream.start_stream()

    def port_activated(self, port):
        if port == self.reset_port:
            self.stop_stream()
        else:
            self.collect()
        
    def collect(self):
        for edge in self.samples_port.edges:
            if edge.is_activated():
                samples = edge.get()
                samples = (to_numpy(samples).astype('float32')*float(self.gain_control.get())).tobytes()
                self.buffer.put(samples)
                if len(self.buffer) > 44100 * 5:
                    self.print_exception('Buffer overflow')
                    self.buffer = byteFIFO()
        
        if not self.playing and len(self.buffer) > 44100 * 0.00:
            self.playing = True
            self.run(self.start_stream)
        self.set_running(True)
            
    def stop_stream(self):
        if self.stream is not None:
            self.stream.close()
        self.stream = None
        self.buffer = byteFIFO()
        self.set_running(False)
        self.playing = False
        print('Stream stopped')

    def callback(self, in_data, frame_count, time_info, status):
        if self.is_destroyed():
            return (None, pyaudio.paComplete)
        #print(f'requested {frame_count} frames, buffer size: {len(self.buffer)} {time_info}')
        if len(self.buffer) < frame_count * 4:
            print('Buffer underflow')
            data = self.buffer.getvalue()
            data = bytes(data)
            self.stop_stream()
            return (data, pyaudio.paComplete)
        
        data = self.buffer.get(frame_count * 4)
        data = bytes(data)

        self.delay_update_i = (self.delay_update_i+1)%100
        if self.delay_update_i == 0:
            self.delay_control.set(f'{len(self.buffer)/4/44100*1000:.2f} ms')
        
        return (data, pyaudio.paContinue)

    def destroy(self) -> SObjectSerialized:
        if not self.is_preview.get():
            self.stop_stream()
            self.p.terminate()
        return super().destroy()