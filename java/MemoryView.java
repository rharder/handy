import javax.swing.*;
import java.awt.*;
import java.awt.event.*;
import java.lang.reflect.Method;
import java.text.MessageFormat;
import java.text.NumberFormat;

/**
 * (Note, this is a class I wrote about 20 years ago.  I just carry it along on my projects. -Rob)
 *
 * Frame to display amount of free memory in the running application.
 * <p>
 * Handy for use with NetBeans Developer's internal execution. Then the statistic
 * of free memory in the whole environment is displayed.
 *
 * @version 1.0
 * @author Robert Harder, rob@iharder.net
 * license Public Domain
 */
public class MemoryView extends javax.swing.JFrame {

    /**
     * message of free memory
     */
    private static MessageFormat msgMemory = new MessageFormat("Used {2} of {0} {3} allocated memory");

    private static String HOW_TO_TOOLTIP = "With the memoryview.jar file in your classpath, use this tool by calling: new MemoryView()";

    private final static String[] UNITS_TEXT =
            {"bytes", "Kb", "Mb", "Gb"};
    private final static double[] UNITS_DIVISOR =
            {1, 1024, 1024 * 1024, 1024 * 1024 * 1024};

    private int unitsIndexCounter = 2;
    private NumberFormat nf;

    /**
     * default update time
     */
    private final static int UPDATE_TIME = 1000;
    /**
     * timer to invoke updating
     */
    private Timer timer;

    public MemoryView() {
        this("Memory View");
    }

    /**
     * Initializes the Form
     */
    public MemoryView(String title) {
        initComponents();

        setTitle(title);
        doGarbage.setText("Collect Garbage");
        doRefresh.setText("Refresh");
        doClose.setText("Close");

        txtTime.setText("Refresh millis");
        doTime.setText("Set refresh");
        time.setText(String.valueOf(UPDATE_TIME));
        time.selectAll();
        time.requestFocus();

        updateStatus();

        timer = new Timer(UPDATE_TIME, new ActionListener() {
            public void actionPerformed(ActionEvent ev) {
                updateStatus();
            }
        });
        timer.setRepeats(true);

        pack();

        Dimension d = Toolkit.getDefaultToolkit().getScreenSize();
        Dimension m = this.getSize();
        d.width -= m.width;
        d.height -= m.height;
        d.width /= 2;
        d.height /= 2;
        this.setLocation(d.width, d.height);
        this.setVisible(true);

    }


    /**
     * Starts the timer.
     */
    public void addNotify() {
        super.addNotify();
        timer.start();
    }

    /**
     * Stops the timer.
     */
    public void removeNotify() {
        try {
            super.removeNotify();
            timer.stop();
            timer = null;
        }   // end try
        catch (Exception e) {
        }
    }

    /**
     * Updates the status of all components
     */
    private void updateStatus() {
        Runtime r = Runtime.getRuntime();
        long free = r.freeMemory();
        long total = r.totalMemory();
        long taken = total - free;


        // Divide by necessary amount for units
        //free /= UNITS_DIVISOR[ unitsIndexCounter%UNITS_DIVISOR.length ];
        //total/= UNITS_DIVISOR[ unitsIndexCounter%UNITS_DIVISOR.length ];

        // when bigger than integer then divide by two
        long liTotal = total;
        long liFree = free;
        while (liTotal > Integer.MAX_VALUE) {
            liTotal = liTotal >> 1;
            liFree = liFree >> 1;
        }
        long liTaken = (int) (liTotal - liFree);

        status.setMaximum((int) liTotal);
        status.setValue((int) liTaken);

        text.setText(msgMemory.format(new Object[]{
                nf.format(total / UNITS_DIVISOR[unitsIndexCounter]),
                nf.format(free / UNITS_DIVISOR[unitsIndexCounter]),
                nf.format(taken / UNITS_DIVISOR[unitsIndexCounter]),
                UNITS_TEXT[unitsIndexCounter % UNITS_TEXT.length]
        }));
        text.invalidate();
        validate();
    }

    /**
     * This method is called from within the constructor to
     * initialize the form.
     */
    private void initComponents() {
        nf = NumberFormat.getInstance();
        nf.setMaximumFractionDigits(1);
        nf.setMinimumIntegerDigits(1);

        jPanel1 = new javax.swing.JPanel();
        text = new javax.swing.JLabel();
        status = new javax.swing.JProgressBar();
        jPanel2 = new javax.swing.JPanel();
        doGarbage = new javax.swing.JButton();
        doRefresh = new javax.swing.JButton();
        doClose = new javax.swing.JButton();
        jPanel3 = new javax.swing.JPanel();
        jPanel3.setToolTipText(HOW_TO_TOOLTIP);
        txtTime = new javax.swing.JLabel();
        time = new javax.swing.JTextField();
        doTime = new javax.swing.JButton();
        addWindowListener(new WindowAdapter() {
            public void windowClosing(WindowEvent evt) {
                exitForm(evt);
            }
        });   // end windowadapter

        //Listen for clicks to label
        text.addMouseListener(new MouseAdapter() {
            public void mouseClicked(MouseEvent e) {
                unitsIndexCounter = (unitsIndexCounter + 1) % UNITS_DIVISOR.length;
            }   // end mouseClicked
        });
        text.setToolTipText("Click to change units");

        jPanel1.setLayout(new java.awt.BorderLayout());


        jPanel1.add(text, java.awt.BorderLayout.SOUTH);


        jPanel1.add(status, java.awt.BorderLayout.CENTER);


        getContentPane().add(jPanel1, java.awt.BorderLayout.CENTER);


        doGarbage.addActionListener(new ActionListener() {
                                        public void actionPerformed(ActionEvent evt) {
                                            doGarbageActionPerformed(evt);
                                        }
                                    }
        );

        jPanel2.add(doGarbage);

        doRefresh.addActionListener(new ActionListener() {
                                        public void actionPerformed(ActionEvent evt) {
                                            doRefreshActionPerformed(evt);
                                        }
                                    }
        );

        jPanel2.add(doRefresh);

        doClose.addActionListener(new ActionListener() {
                                      public void actionPerformed(ActionEvent evt) {
                                          doCloseActionPerformed(evt);
                                      }
                                  }
        );

        jPanel2.add(doClose);


        getContentPane().add(jPanel2, java.awt.BorderLayout.SOUTH);

        jPanel3.setLayout(new java.awt.BorderLayout(0, 20));


        jPanel3.add(txtTime, java.awt.BorderLayout.WEST);


        jPanel3.add(time, java.awt.BorderLayout.CENTER);

        doTime.addActionListener(new ActionListener() {
                                     public void actionPerformed(ActionEvent evt) {
                                         setRefreshTime(evt);
                                     }
                                 }
        );

        jPanel3.add(doTime, java.awt.BorderLayout.EAST);


        getContentPane().add(jPanel3, java.awt.BorderLayout.NORTH);

    }

    /**
     * Exit the form
     */
    private void exitForm(WindowEvent evt) {
        removeNotify();
        dispose();
        //System.exit( 0 );
    }

    private void setRefreshTime(ActionEvent evt) {
        try {
            int rate = Integer.valueOf(time.getText()).intValue();
            timer.setDelay(rate);
        } catch (NumberFormatException ex) {
            time.setText(String.valueOf(timer.getDelay()));
        }
        time.selectAll();
        time.requestFocus();
    }


    private void doCloseActionPerformed(ActionEvent evt) {
        exitForm(null);
    }


    private void doRefreshActionPerformed(ActionEvent evt) {
        updateStatus();
    }

    private void doGarbageActionPerformed(ActionEvent evt) {
        System.gc();
        updateStatus();
    }


    // Variables declaration - do not modify
    private javax.swing.JPanel jPanel1;
    private javax.swing.JLabel text;
    private javax.swing.JProgressBar status;
    private javax.swing.JPanel jPanel2;
    private javax.swing.JButton doGarbage;
    private javax.swing.JButton doRefresh;
    private javax.swing.JButton doClose;
    private javax.swing.JPanel jPanel3;
    private javax.swing.JLabel txtTime;
    private javax.swing.JTextField time;
    private javax.swing.JButton doTime;
    // End of variables declaration


    /**
     * Opens memory view window in middle of screen
     */
    @SuppressWarnings("unchecked")
    public static void main(String[] args) {

        MemoryView mv = new MemoryView();

        // See if there are at least two arguments. One would be the
        // -launch flag and the second should be a class. Pass the
        // remaining arguments to the launching program.
        try {
            if (args[0].equals("-launch")) {
                String[] args2 = new String[args.length - 2];
                for (int i = 2; i < args.length; i++)
                    args2[i - 2] = args[i];
                Object[] newargs = {args2};
                //ClassLoader cl = mv.getClass().getClassLoader();
                ClassLoader cl = ClassLoader.getSystemClassLoader();
                Class c = cl.loadClass(args[1]);
                Class[] cs = {String[].class};
                Method m = c.getMethod("main", cs);
                m.invoke(null, newargs);
            }   // end if: launch given
        }   // end try
        catch (Exception e) {   //e.printStackTrace();
            System.out.println("Alternate usage: java MemoryView [-launch ClassToLaunch [arg1 arg2 ...] ]");
        }


    }

}
