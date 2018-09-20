import itertools

import fluteline
import time
import watson_streaming


class IBMWatsonAdapter(fluteline.Consumer):
    '''
    A fluteline consumer-producer that receives transcription from
    :class:`watson_streaming.Transcriber` and prepare them to work
    with the deep_disfluency tagger.
    '''
    def enter(self):
        self.running_id = itertools.count()
        # Messages that went down the pipeline, indexed by start_time.
        self.memory = {}
        # Track when Watson commits changes to clear the memory.
        self.result_index = 0

    def consume(self, data):
        if 'results' in data:
            self.clear_memory_if_necessary(data)
            for t in data['results'][0]['alternatives'][0]['timestamps']:
                self.process_timestamp(t)

    def clear_memory_if_necessary(self, data):
        if data['result_index'] > self.result_index:
            self.memory = {}
            self.result_index = data['result_index']

    def process_timestamp(self, timestamp):
        word, start_time, end_time = timestamp
        word = self.clean_word(word)

        if self.is_new(start_time):
            id_ = next(self.running_id)
        else:
            id_ = self.get_id_if_update(start_time, end_time, word)

        if id_ is not None:
            msg = {
                'start_time': start_time,
                'end_time': end_time,
                'word': word,
                'id': id_
            }
            self.memory[start_time] = msg
            self.output.put(msg)


    def clean_word(self, word):
        if word in ['mmhm', 'aha', 'uhhuh']:
            return 'uh-huh'
        if word == '%HESITATION':
            return 'uh'
        return word

    def is_new(self, start_time):
        if len(self.memory.keys()) == 0:
            return True
        last_update = sorted(self.memory.keys(), reverse=True)[0]
        return start_time >= self.memory[last_update]['end_time']

    def get_id_if_update(self, start_time, end_time, word):
        """Returns the first id being updated.
        Removes/revokes the ids also implicitly being removed
        (i.e. the words chronologically after the update.
        If no update return None."""
        if self.memory.get(start_time):
            old_start_time = self.memory[start_time]['start_time']
            old_end_time = self.memory[start_time]['end_time']
            old_word = self.memory[start_time]['word']
            if (start_time, end_time, word) == (old_start_time,
                                                old_end_time, old_word):
                return None  # a repeated word
        update_id = None
        update_start_times_to_revoke = []
        for old_id in sorted(self.memory.keys(), reverse=True):
            if start_time >= self.memory[old_id]['end_time']:
                # we've found the update
                break
            update_start_times_to_revoke.append(old_id)
            update_id = self.memory[old_id]['id']
        for start_time in update_start_times_to_revoke:
            self.memory.pop(start_time, None)
        self.running_id = itertools.count(update_id+1)  # set the counter
        return update_id
