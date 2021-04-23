import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Helps with handling command line arguments.
 */
public class SysArgs {

    private String[] commandLineArgs;

    // Experimental
    private List<PositionalArg> positionalArgTypes = new ArrayList<>();
    private List<ArgType> namedArgTypes;

    public SysArgs() {
        this.commandLineArgs = new String[]{};
    }

    /**
     * Normal entry point for this class. Example:
     * <p>
     * public static void main(String[] args) {
     * SysArgs sysArgs = new SysArgs(args);
     * ...
     * }
     */
    public SysArgs(String[] commandLineArgs) {
        this.commandLineArgs = Objects.requireNonNull(commandLineArgs);
    }

    public void setCommandLineArgs(String[] commandLineArgs) {
        this.commandLineArgs = Objects.requireNonNull(commandLineArgs);
    }

    public String[] getCommandLineArgs() {
        return this.commandLineArgs;
    }

    public int length() {
        return getCommandLineArgs().length;
    }

    public void addPositionalArgType(PositionalArg arg) {
        this.positionalArgTypes.add(arg);
    }

    public void addNamedArgType(NamedArg t) {
        this.namedArgTypes.add(t);
    }

    public void processArgs(String[] args) {

        for (int i = 0; i < args.length; i++) {

        }
    }

    public void addArg(String arg1) {
        String[] args2 = new String[this.commandLineArgs.length];
        System.arraycopy(this.commandLineArgs, 0, args2, 0, this.commandLineArgs.length);
        args2[args2.length - 1] = arg1;
        this.commandLineArgs = args2;
    }

    public void addArgs(String... addlArgs) {
        String[] args2 = new String[this.commandLineArgs.length + addlArgs.length];
        System.arraycopy(this.commandLineArgs, 0, args2, 0, this.commandLineArgs.length);
        System.arraycopy(addlArgs, 0, args2, this.commandLineArgs.length, addlArgs.length);
        this.commandLineArgs = args2;
    }

    /**
     * Whether or not the arg exists.
     */
    public boolean hasArg(String arg1) {
        return SysArgs.hasArg(getCommandLineArgs(), arg1);
    }

    /**
     * Whether or not an arg exists and there is another arg after it.
     */
    public boolean hasArgWithArgument(String arg1) {
        return getStringArgAfter(arg1).isPresent();
    }

    /**
     * Returns the string after the given arg, or Optional.empty() if not there.
     */
    public Optional<String> argAfter(String arg1) {
        return SysArgs.argAfter(getCommandLineArgs(), arg1);
    }

    /**
     * Returns the arg asked for or Optional.empty() if not present.
     */
    public Optional<String> arg(String arg1) {
        return hasArg(arg1) ? Optional.of(arg1) : Optional.empty();
    }

    /**
     * Returns the arg at the given index (zero-indexed)
     * or Optional.empty() if there are not enough args.
     */
    public Optional<String> getStringArg(int pos) {
        String[] args = getCommandLineArgs();
        if (pos < args.length) {
            return Optional.of(args[pos]);
        }
        return Optional.empty();
    }

    /**
     * Returns the arg after the given arg or Optional.empty() if that
     * arg does not exist or there is no arg after it.
     */
    public Optional<String> getStringArgAfter(String arg1) {
        for (int i = 0; i < commandLineArgs.length - 1; i++) {
            if (commandLineArgs[i].equals(arg1)) {
                return Optional.of(commandLineArgs[i + 1]);
            }
        }
        return Optional.empty();
    }

    /**
     * Returns a list of arg values that come after a given arg that is possible to repeat.
     * Example command line where this might be useful:
     * <p>
     * MyApp --merge-file file1.txt --merge-file file2.txt --merge-file file3.txt
     */
    public List<String> getStringArgsAfterAllInstances(String arg1) {
        List<String> results = new ArrayList<>();
        for (int i = 0; i < commandLineArgs.length - 1; i++) {
            if (commandLineArgs[i].equals(arg1)) {
                results.add(commandLineArgs[i + 1]);
                i++;  // Skip the arg
            }
        }
        return results;
    }

    /**
     * Returns an int after the given arg or Optional.empty() if it does not exist
     * or is not an integer.
     * <p>
     * (I wonder if I want this to throw some kind of exception but for now, no. -Rob)
     */
    public Optional<Integer> getIntArgAfter(String arg1) {
        try {
            return getStringArgAfter(arg1).map(Integer::parseInt);
        } catch (NumberFormatException ex) {
            System.err.println(ex + " Invalid integer value for " + arg1);
            return Optional.empty();
        }
    }

//    // TODO: add the all instances thing for these numberics too
//    public List<Integer> getIntArgsAfterAllInstances(String arg1) {
//        List<Integer> results = new ArrayList<>();
//        return getStringArgsAfterAllInstances(arg1).stream().map(Integer::parseInt).collect(Collectors.toList());
////        for(String s : getStringArgsAfterAllInstances(arg1)){
////
////        }
////        return results;
//    }

    /**
     * Returns a floating point double after the given arg or Optional.empty() if it does not exist
     * or is not a valid double.
     * <p>
     * (I wonder if I want this to throw some kind of exception but for now, no. -Rob)
     */
    public Optional<Double> getDoubleArgAfter(String arg1) {
        try {
            return getStringArgAfter(arg1).map(Double::parseDouble);
        } catch (NumberFormatException ex) {
            System.err.println(ex + " Invalid double value for " + arg1);
            return Optional.empty();
        }
    }

    /**
     * Whether or not an arg exists.
     * Similar in purpose to {@link #arg(String)} but different in usage.
     */
    public static boolean hasArg(String[] args, String arg1) {
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals(arg1)) {
                return true;
            }
        }
        return false;
    }
//
//    /**
//     * Looks for an argument in the list and verifies that it also has an argument following it.
//     */
//    public static boolean hasArgWithArgument(String[] args, String arg1) {
//        for (int i = 0; i < args.length - 1; i++) {
//            if (args[i].equals(arg1)) {
//                return true;
//            }
//        }
//        return false;
//    }

    /**
     * Returns the string after the given arg, or Optional.empty() if not there.
     */
    public static Optional<String> argAfter(String[] args, String arg1) {
        for (int i = 0; i < args.length - 1; i++) {
            if (args[i].equals(arg1)) {
                return Optional.of(args[i + 1]);
            }
        }
        return Optional.empty();
//        throw new RuntimeException("The required argument after " + arg1 + " was missing: " + args);
    }

    public static void main(String[] args) {
        args = new String[]{"--port", "Z1234Z"};
        SysArgs sysArgs = new SysArgs(args);

        sysArgs.addNamedArgType(new NamedArg("--port"));
        sysArgs.processArgs(args);

        System.out.println(sysArgs.getIntArgAfter("--port").orElse(5678));


    }

    /* *******  E X P E R I M E N T A L ******** */

    protected interface ArgType {

    }

    protected static class PositionalArg implements ArgType {
        protected String name;
        //        protected String help;
        protected String value;

        protected PositionalArg() {

        }

        protected PositionalArg(String name) {
            this.name = name;
        }

//        protected PositionalArg(String name, String help) {
//            this.name = name;
//            this.help = help;
//        }

        protected void setValue(String val) {
            this.value = val;
        }

        protected String getValue() {
            return null;
        }

//        @Override
//        public String getHelp() {
//            return help;
//        }
    }

    protected static class PositionalIntegerArg extends PositionalArg {
        public PositionalIntegerArg() {
        }

        public PositionalIntegerArg(String name) {
            super(name);
        }

//        public PositionalIntegerArg(String name, String help) {
//            super(name, help);
//        }

        protected int getInt() {
            return Integer.parseInt(getValue());
        }
    }

    protected static class NamedArg implements ArgType {
        private String longForm;

        protected NamedArg(String longForm) {
            this.longForm = longForm;
        }

    }

    protected static class FlagArg implements ArgType {
        String longArg;
        String help;

        protected FlagArg(String longArg, String help) {
            this.longArg = longArg;
            this.help = help;
        }

//        @Override
//        public String getLongArg() {
//            return longArg;
//        }
//
//        @Override
//        public String getHelp() {
//            return help;
//        }
    }


}
