from llmAgent import LlmAgent
import yarp
import sys
import re

def icub_msg(text):
    print("\033[93m{}\033[00m".format(text))
def info(msg):
    print("[INFO] {}".format(msg))
def warn(msg):
    print("\033[93m[WARNING] {}\033[00m".format(msg))
def error(msg):
    print("\033[91m[ERROR] {}\033[00m".format(msg))
def debug(msg):
    # print in cyan
    print("\033[96m[DEBUG] {}\033[00m".format(msg))


class CommunicationReasoner(yarp.RFModule):

    def __init__(self):
        yarp.RFModule.__init__(self)

        self.module_name = None

        self.llm_model_name = None
        self.llm_agent = None
        self.repetition_penalty = None
        self.max_new_tokens = None
        self.temperature = None
        self.top_p = None
        self.top_k = None
        self.DEBUG_MODE = False
        self.addressee = None
        self.history = []

        self.handle_port = yarp.Port()
        self.attach(self.handle_port)
        self.speech_input_port = yarp.BufferedPortBottle()
        self.answer_port = yarp.Port()
        self.spatial_memory_rpc_port = yarp.RpcClient()
        self.spatial_memory_rpc_port.setRpcMode(True)

    def configure(self, rf):
        # Configure module parameters
        self.module_name = rf.check("name",
                                    yarp.Value("communicationReasoner"),
                                    "module name (string)").asString()

        self.llm_model_name = rf.check("llm_model_name",
                                       yarp.Value("https://osanseviero-mistral-super-fast.hf.space/"),
                                       "name of the llm model (str)").asString()

        self.top_k = rf.check("top_k",
                              yarp.Value(50),
                              "top_k (int)").asInt8()

        self.top_p = rf.check("top_p",
                              yarp.Value(0.9),
                              "top_p (float)").asFloat64()

        self.temperature = rf.check("temperature",
                                    yarp.Value(0.7),
                                    "temperature (float)").asFloat64()

        self.max_new_tokens = rf.check("max_new_tokens",
                                       yarp.Value(100),
                                       "max_tokens (int)").asInt16()

        self.repetition_penalty = rf.check("repetition_penalty",
                                           yarp.Value(1.2),
                                           "repetition_penalty (float)").asFloat64()


        # print all the parameters
        print("\n-------------------------------------------------------")
        info("Parameters:")
        info("module_name: {}".format(self.module_name))
        info("model_name: {}".format(self.llm_model_name))
        info("top_k: {}".format(self.top_k))
        info("top_p: {}".format(self.top_p))
        info("temperature: {}".format(self.temperature))
        info("max_tokens: {}".format(self.max_new_tokens))
        info("repetition_penalty: {}".format(self.repetition_penalty))
        print("-------------------------------------------------------\n")

        self.llm_agent = LlmAgent(
            model_name=self.llm_model_name,
            temperature=self.temperature,
            max_new_tokens=self.max_new_tokens,
            top_p=self.top_p,
            repetition_penalty=self.repetition_penalty,
        )

        ########## PORTS ##########
        self.handle_port.open('/' + self.module_name)
        self.speech_input_port.open('/' + self.module_name + '/prompt:i')
        self.spatial_memory_rpc_port.open('/' + self.module_name + '/spatialMemory:rpc')
        self.answer_port.open('/' + self.module_name + '/answer:o')

        return True

    def respond(self, command, reply):
        reply.clear()
        return True

    def getPeriod(self):
        """
           Module refresh rate.
           Returns : The period of the module in seconds.
        """
        return 0.05

    def updateModule(self):

        if self.DEBUG_MODE:
            prompt = input("Enter the prompt: ")
            addressee = input("Enter the addressee: ")
        else:
            prompt, addressee = self.read_prompt()

        if prompt is not None:
            answer = ""
            if addressee == "robot":
                debug("ADDRESSEE is ROBOT and prompt was {}".format(prompt))

                answer = self.llm_agent.chat(prompt, self.history)
                icub_msg(answer)

                if answer is not None:
                    acapela_text = " \\mrk=0\\ " + self.clean_for_acapela(answer) + " \\mrk=1\\ ."
                    # info("Sending to acapela the following text: {}".format(acapela_text))
                    self.send_to_acapela(acapela_text)
            else:
                debug("Prompt was '{}' but addressee was not robot. Keep attending the conversation".format(prompt))

            self.history.append(prompt) # "[user_prompt]: " +
            self.history.append(answer) # "[robot_answer]: " +

        return True

    def interruptModule(self):
        self.speech_input_port.interrupt()
        self.spatial_memory_rpc_port.interrupt()
        self.answer_port.interrupt()
        return True

    def close(self):
        self.speech_input_port.close()
        self.spatial_memory_rpc_port.close()
        self.answer_port.close()
        return True

    def clean_for_acapela(self, text):
        # Rimuove le parti racchiuse tra <>
        text = re.sub(r'[\<].*?[\>]', '', text)
        return text

    def send_to_acapela(self, msg):
        """
        Send text to the speak module
        :param msg:
        :return: None
        """
        speak_bottle = yarp.Bottle()
        speak_bottle.clear()
        speak_bottle.addString(msg)
        self.answer_port.write(speak_bottle)

        return True

    def read_prompt(self):
        question = None
        addressee = None
        if self.speech_input_port.getInputCount():
            input_bottle = self.speech_input_port.read(False)
            #print("reading from input port")
            if input_bottle is not None:
                question = input_bottle.get(0).asString()
                addressee = input_bottle.get(1).asString()

        return question, addressee


if __name__ == '__main__':

    # Initialise YARP
    if not yarp.Network.checkNetwork():
        print("Unable to find a yarp server exiting ...")
        sys.exit(1)

    yarp.Network.init()
    communicationReasoner = CommunicationReasoner()

    rf = yarp.ResourceFinder()
    rf.setVerbose(True)
    rf.setDefaultContext('communicationReasoner')
    rf.setDefaultConfigFile('communicationReasoner.ini')

    if rf.configure(sys.argv):
        communicationReasoner.runModule(rf)

    sys.exit()









