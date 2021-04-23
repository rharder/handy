/**
 * This class makes it easy to drag and drop files from the operating
 * system to a Java program. Any <tt>java.awt.Component</tt> can be
 * dropped onto, but only <tt>javax.swing.JComponent</tt>s will indicate
 * the drop event with a changed border.
 * <p/>
 * To use this class, construct a new <tt>FileDrop</tt> by passing
 * it the target component and a <tt>Listener</tt> to receive notification
 * when file(s) have been dropped. Here is an example:
 * <p/>
 * <code><pre>
 *      JPanel myPanel = new JPanel();
 *      new FileDrop( myPanel, new FileDrop.Listener()
 *      {   
 *          public void filesDropped( java.io.File[] files, java.awt.dnd.DropTargetDropEvent evt )
 *          {   
 *              // handle file drop
 *              ...
 *          }   // end filesDropped
 *      }); // end FileDrop.Listener
 * </pre></code>
 * <p/>
 *
 * If you don't care about the drag and drop event (I suspect most of you won't) then
 * can safely ignore the <tt>evt</tt> parameter shown above. Try this:
 * <p />
 * <code><pre>public void filesDropped( java.io.File[] files, Object ignoreMe )</pre></code>
 *
 *
 * You can specify the border that will appear when files are being dragged by
 * calling the constructor with a <tt>javax.swing.border.Border</tt>. Only
 * <tt>JComponent</tt>s will show any indication with a border.
 * <p/>
 *
 * <p>I'm releasing this code into the Public Domain. Enjoy.
 * </p>
 * <p><em>Original author: Robert Harder, rob@iharder.net</em></p>
 *
 * @author  Robert Harder
 * @author  rob@iharder.net
 * @version 1.1
 */
public class FileDrop
{
    private transient javax.swing.border.Border normalBorder;
    private transient java.awt.dnd.DropTargetListener dropListener;
    
    
    /** Discover if the running JVM is modern enough to have drag and drop. */
    private static Boolean supportsDnD;
    
    // Default border color
    private static java.awt.Color defaultBorderColor = new java.awt.Color( 0f, 0f, 1f, 0.25f );
    
    /**
     * Constructs a {@link FileDrop} with a default light-blue border
     * and, if <var>c</var> is a {@link java.awt.Container}, recursively
     * sets all elements contained within as drop targets, though only
     * the top level container will change borders.
     *
     * @param c Component on which files will be dropped.
     * @param listener Listens for <tt>filesDropped</tt>.
     * @since 1.0
     */
    public FileDrop( java.awt.Component c, Listener listener )
    {
        this( c,     // Drop target
              javax.swing.BorderFactory.createMatteBorder( 2, 2, 2, 2, defaultBorderColor ), // Drag border
              true, // Recursive
              listener );
    }   // end constructor
    
        
    
    /**
     * Full constructor.
     *
     * @param c Component on which files will be dropped.
     * @param dragBorder Border to use on <tt>JComponent</tt> when dragging occurs.
     * @param recursive Recursively set children as drop targets.
     * @param listener Listens for <tt>filesDropped</tt>.
     * @since 1.0
     */
    public FileDrop( final java.awt.Component c, final javax.swing.border.Border dragBorder, final boolean recursive, final Listener listener) 
    {   
        
        if( supportsDnD() )
        {   
            // Make a drop listener
            dropListener = new java.awt.dnd.DropTargetListener()
            {	
                // Drag enter event
                public void dragEnter( java.awt.dnd.DropTargetDragEvent evt )
                {	
                    // Is this an acceptable drag event?
                    if( isDragOk( evt ) )
                    {
                        // If it's a Swing component, set its border
                        if( c instanceof javax.swing.JComponent )
                        {   
                            javax.swing.JComponent jc = (javax.swing.JComponent) c;
                            normalBorder = jc.getBorder();  // Save normal (original) border
                            jc.setBorder( dragBorder );     // Set border
                        }   // end if: JComponent   

                        // Acknowledge that it's okay to enter
                        //evt.acceptDrag( java.awt.dnd.DnDConstants.ACTION_COPY_OR_MOVE );
                        evt.acceptDrag( java.awt.dnd.DnDConstants.ACTION_COPY );
                        
                    }   // end if: drag ok
                    else 
                    {   
                        // Reject the drag event
                        evt.rejectDrag();
                    }   // end else: drag not ok
                }   // end dragEnter
                
                // This is called continually as long as the mouse is
                // over the drag target.
                public void dragOver( java.awt.dnd.DropTargetDragEvent evt ) 
                {   
                }   // end dragOver

                // Drop event
                public void drop( java.awt.dnd.DropTargetDropEvent evt )
                {   
                    try
                    {   // Get whatever was dropped
                        java.awt.datatransfer.Transferable tr = evt.getTransferable();

                        // Is it a file list?
                        if( tr.isDataFlavorSupported( java.awt.datatransfer.DataFlavor.javaFileListFlavor ) )
                        {
                            // Say we'll take it.
                            //evt.acceptDrop ( java.awt.dnd.DnDConstants.ACTION_COPY_OR_MOVE );
                            evt.acceptDrop ( java.awt.dnd.DnDConstants.ACTION_COPY );

                            // Get a useful list
                            java.util.List fileList = 
                                (java.util.List)tr.getTransferData( java.awt.datatransfer.DataFlavor.javaFileListFlavor );
                            java.util.Iterator iterator = fileList.iterator();

                            // Convert list to array
							java.io.File[] filesTemp = (java.io.File[])fileList.toArray();
                            final java.io.File[] files = filesTemp;

                            // Alert listener to drop.
                            if( listener != null )
                                listener.filesDropped( files, evt );

                            // Mark that drop is completed.
                            evt.getDropTargetContext().dropComplete( true );
                            
                        }   // end if: file list
                        else 
                        {   
                            evt.rejectDrop();
                        }   // end else: not a file list
                    }   // end try
                    catch ( java.io.IOException io) 
                    {   
                        io.printStackTrace();
                        evt.rejectDrop();
                    }   // end catch IOException
                    catch (java.awt.datatransfer.UnsupportedFlavorException ufe) 
                    {   
                        ufe.printStackTrace();
                        evt.rejectDrop();
                    }   // end catch: UnsupportedFlavorException
                    finally
                    {
                        // If it's a Swing component, reset its border
                        if( c instanceof javax.swing.JComponent )
                        {   
                            javax.swing.JComponent jc = (javax.swing.JComponent) c;
                            jc.setBorder( normalBorder );
                            
                        }   // end if: JComponent
                    }   // end finally
                }   // end drop

                public void dragExit( java.awt.dnd.DropTargetEvent evt ) 
                {   
                    // If it's a Swing component, reset its border
                    if( c instanceof javax.swing.JComponent )
                    {   
                        javax.swing.JComponent jc = (javax.swing.JComponent) c;
                        jc.setBorder( normalBorder );
                        
                    }   // end if: JComponent
                }   // end dragExit

                public void dropActionChanged( java.awt.dnd.DropTargetDragEvent evt ) 
                {   
                    // Is this an acceptable drag event?
                    if( isDragOk( evt ) )
                    {   
                        //evt.acceptDrag( java.awt.dnd.DnDConstants.ACTION_COPY_OR_MOVE );
                        evt.acceptDrag( java.awt.dnd.DnDConstants.ACTION_COPY );
                        
                    }   // end if: drag ok
                    else 
                    {   
                        evt.rejectDrag();
                    }   // end else: drag not ok
                }   // end dropActionChanged
            }; // end DropTargetListener

            // Make the component (and possibly children) drop targets
            makeDropTarget( c, recursive );
        }   // end if: supports dnd
        else
        {   
            System.err.println( "File drag and drop is not supported with this JVM" );
        }   // end else: does not support DnD
    }   // end constructor

    
    private static boolean supportsDnD()
    {   
        // Static Boolean
        if( supportsDnD == null )
        {   
            boolean support = false;
            try
            {   
                Class arbitraryDndClass = Class.forName( "java.awt.dnd.DnDConstants" );
                support = true;
            }   // end try
            catch( Exception e )
            {   
                support = false;
            }   // end catch
            
            supportsDnD = new Boolean( support );
            
        }   // end if: first time through
        
        return supportsDnD.booleanValue();
    }   // end supportsDnD
    
    
    
    private void makeDropTarget( final java.awt.Component c, final boolean recursive )
    {
        // Make drop target
        java.awt.dnd.DropTarget dt = new java.awt.dnd.DropTarget();
        try
        {   
            dt.addDropTargetListener( dropListener );
        }   // end try
        catch( java.util.TooManyListenersException e )
        {   
            e.printStackTrace();
        }   // end catch
        
        // Listen for hierarchy changes and remove the drop target when the parent gets cleared out.
        c.addHierarchyListener( new java.awt.event.HierarchyListener()
        {   
            public void hierarchyChanged( java.awt.event.HierarchyEvent evt )
            {
                java.awt.Component parent = c.getParent();
                if( parent == null )
                {   
                    c.setDropTarget( null );
                    
                }   // end if: null parent
                else
                {   
                    new java.awt.dnd.DropTarget(c, dropListener);
                    
                }   // end else: parent not null
            }   // end hierarchyChanged
        }); // end hierarchy listener
        
        if( c.getParent() != null )
            new java.awt.dnd.DropTarget(c, dropListener);
        
        if( recursive && (c instanceof java.awt.Container ) )
        {   
            // Get the container
            java.awt.Container cont = (java.awt.Container) c;
            
            // Get it's components
            java.awt.Component[] comps = cont.getComponents();
            
            // Set it's components as listeners also
            for( int i = 0; i < comps.length; i++ )
                makeDropTarget( comps[i], recursive );
            
        }   // end if: recursively set components as listener
    }   // end dropListener
    
    
    
    /** Determine if the dragged data is a file list. */
    private boolean isDragOk( java.awt.dnd.DropTargetDragEvent evt )
    {   
        boolean ok = false;
        
        // Get data flavors being dragged
        java.awt.datatransfer.DataFlavor[] flavors = evt.getCurrentDataFlavors();
        
        // See if any of the flavors are a file list
        int i = 0;
        while( !ok && i < flavors.length )
        {   
            // Is the flavor a file list?
            if( flavors[i].equals( java.awt.datatransfer.DataFlavor.javaFileListFlavor ) )
                ok = true;            
            i++;
        }   // end while: through flavors
        
        return ok;
    }   // end isDragOk
    
    
    
    /**
     * Removes the drag-and-drop hooks from the component and optionally
     * from the all children. You should call this if you add and remove
     * components after you've set up the drag-and-drop.
     * This will recursively unregister all components contained within
     * <var>c</var> if <var>c</var> is a {@link java.awt.Container}.
     *
     * @param c The component to unregister as a drop target
     * @since 1.0
     */
    public static boolean remove( java.awt.Component c)
    {   
        return remove( c, true );
    }   // end remove
    
    
    
    /**
     * Removes the drag-and-drop hooks from the component and optionally
     * from the all children. You should call this if you add and remove
     * components after you've set up the drag-and-drop.
     *
     * @param c The component to unregister
     * @param recursive Recursively unregister components within a container
     * @since 1.0
     */
    public static boolean remove( java.awt.Component c, boolean recursive )
    {   
        // Make sure we support dnd.
        if( supportsDnD() )
        {   
            c.setDropTarget( null );
            if( recursive && ( c instanceof java.awt.Container ) )
            {   
                java.awt.Component[] comps = ((java.awt.Container)c).getComponents();
                
                for( int i = 0; i < comps.length; i++ )
                    remove( comps[i], recursive );
                
                return true;
            }   // end if: recursive
            else return false;
        }   // end if: supports DnD
        else return false;
    }   // end remove
    
    
    
    

    /** Runs a sample program that shows dropped files */
    public static void main( String[] args )
    {
        
        // Set up a frame using the normal listener
        javax.swing.JFrame frame = new javax.swing.JFrame( "FileDrop" );
        final javax.swing.JTextArea text = new javax.swing.JTextArea();
        frame.getContentPane().add( 
            new javax.swing.JScrollPane( text ), 
            java.awt.BorderLayout.CENTER );
        
        new FileDrop( text, new FileDrop.Listener()
        {   
            public void filesDropped( java.io.File[] files, java.awt.dnd.DropTargetDropEvent evt )
            // If you don't care about the drag and drop event object:
            // public void filesDropped( java.io.File[] files, Object ignoreMe )
            {   
                for( int i = 0; i < files.length; i++ )
                {   
                    try
                    {   
                        text.append( evt.toString() + "\n" );
                        text.append( files[i].getCanonicalPath() + "\n" );
                    }   // end try
                    catch( java.io.IOException e ) {}
                }   // end for: through each dropped file
            }   // end filesDropped
        }); // end FileDrop.Listener

        frame.setBounds( 100, 100, 300, 400 );
        frame.setDefaultCloseOperation( frame.EXIT_ON_CLOSE );
        frame.setVisible(true);
        
    }   // end main




    
/* ********  I N N E R   I N T E R F A C E   L I S T E N E R  ******** */    
    
    
    /**
     * Implement this inner interface to listen for when files are dropped. For example
     * your class declaration may begin like this:
     * <code><pre>
     *      public class MyClass implements FileDrop.Listener
     *      ...
     *      public void filesDropped( java.io.File[] files )
     *      {
     *          ...
     *      }   // end filesDropped
     *      ...
     * </pre></code>
     *
     * @since 1.0
     */
    public interface Listener
    {   
        /**
         * This method is called when files have been successfully dropped.
         *
         * @param files An array of <tt>File</tt>s that were dropped.
         * @since 1.0
         */
        public abstract void filesDropped( java.io.File[] files, java.awt.dnd.DropTargetDropEvent evt  );
    }   // end inner-interface Listener
    
    
}   // end class FileDrop
