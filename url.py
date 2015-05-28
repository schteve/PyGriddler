import os.path
import re
import sys
import urllib2

# --- Constants ---
CELL_BLANK = 0  # Indicates that we know that a cell is blank, can't have any color there
CELL_EMPTY = -1 # Indicates that we don't know what's in a cell


# --- Functions ---

# This function searches a particular puzzle row for possible solutions, given a list
# of hints and the total width of the puzzle. The list of possibilities is returned.
# Although "row" nomenclature is used, it is equally valid to use this for columns --
# just transpose the hint and actual column to a row before inputting.
def search_possibilities(hints, actual_row, width):
   if len(hints) == 0:
      print "Error: zero length hints list!"
      return []
      
   # Begin recursion with no expansions (everything left shifted), no successes, and
   # a depth of 0.
   expansions = [0 for x in xrange(len(hints))]
   success_list = []
   search_possibilities_recursive(hints, expansions, actual_row, width, 0, success_list)

   return success_list


# This function is a helper for search_possibilities() and should not be called directly.
# It's assumed that len(hints) and len(expansions) are equal!
# Output is maybe_valid_list.
def search_possibilities_recursive(hints, expansions, actual_row, width, depth, maybe_valid_list):
   # Make a full copy of the expansions list because we're going to modify it, and lists are passed
   # by reference so this would propagate up through the recursive calls (which we don't want).
   my_expansions = expansions[:]
   
   #dstring = " "*(depth*3) # depth indentation for prints
   while True:
      current_width = find_used_width(hints, my_expansions)
      #print dstring + "Current width: " + str(current_width)
      if current_width > width:
         #print dstring + "Too big!"
         break
      
      # Recursively try all possibilities
      if len(hints) - depth > 1: # Check here instead of in beginning of function to reduce pointless calls
         search_possibilities_recursive(hints, my_expansions, actual_row, width, depth + 1, maybe_valid_list)
      else:
         # Place the hints and expansions as they are right now and see if it's valid. Row is valid
         # if it fits and doesn't collide with anything already in place.
         test_row = actual_row[:] # Full copy
         test_row_idx = 0
         test_row_valid = True
         try: # Try / except used to break out of nested loop when placement attempt doesn't work
            for h, e in zip(hints, my_expansions):
               # If already beyond width and we haven't placed all hints, then this is invlaid
               if test_row_idx >= width:
                  raise Exception
               
               # Account for two identical consecutive palette ID's.
               if test_row_idx > 0 and test_row[test_row_idx - 1] == h[0]:
                  # Check to make sure there's not something already here. Since we're placing a
                  # spacer (empty) we are OK if it's already blank.
                  if test_row[test_row_idx] != CELL_EMPTY and test_row[test_row_idx] != CELL_BLANK:
                     raise Exception
                     
                  test_row[test_row_idx] = CELL_BLANK
                  test_row_idx = test_row_idx + 1
               
               # First add the expansion. This ALWAYS comes before the corresponding hint.
               for i in xrange(e):
                  # Check to make sure we've not overrun
                  if test_row_idx >= width:
                     raise Exception
                  
                  # Check to make sure there's not something here. If there is and it doesn't match
                  # what we're trying to place bail out!
                  # Expansions can be validly placed over an empty or blank cell.
                  if test_row[test_row_idx] != CELL_EMPTY and test_row[test_row_idx] != CELL_BLANK:
                     raise Exception
                     
                  test_row[test_row_idx] = CELL_BLANK
                  test_row_idx = test_row_idx + 1
                  
               for i in xrange(h[1]):
                  # Check to make sure we've not overrun
                  if test_row_idx >= width:
                     raise Exception
                     
                  # Check to make sure there's not something here. If there is and it doesn't match
                  # what we're trying to place, bail out!
                  # Hints can ONLY be placed over an empty cell. If it's blank then we've
                  # determined that no hint ID can ever go there.
                  if test_row[test_row_idx] != CELL_EMPTY and test_row[test_row_idx] != h[0]:
                     raise Exception
                     
                  test_row[test_row_idx] = h[0]
                  test_row_idx = test_row_idx + 1
            
            # We've placed everything for this test, now make sure there's nothing left in the row.
            while test_row_idx < width:
               # If there's empty cells, mark them as blank so it's clear we intend it that way.
               # If it's already blank, leave it that way. If it's got something there, it's an
               # error so we need to bail (it has something that exceeds the hints).
               if test_row[test_row_idx] == CELL_EMPTY:
                  test_row[test_row_idx] = CELL_BLANK
               elif test_row[test_row_idx] == CELL_BLANK:
                  pass
               else:
                  raise Exception
               
               test_row_idx = test_row_idx + 1
                  
         except Exception:
            test_row_valid = False
         
         # Append to valid possibilities list if... well, valid.
         #print dstring + str(test_row)
         if test_row_valid == True:
            maybe_valid_list.append(test_row)
         else:
            #print dstring + "Doesn't fit!"
            pass
      
      # Increment the leftmost expansion, which corresponds to the current recursion depth.
      # Next pass through the loop we'll search all lower depths with this new value as a base.
      my_expansions[depth] = my_expansions[depth] + 1
      #print ""


# This function collapses a bunch of lists down to a single list. Each position that is the
# same in each input list is marked accordingly in the output list. Any position which has
# variation is marked as an empty cell. It is assumed that each list's length is the same.
def collapse_possibilities(list_of_lists):
   if len(list_of_lists) == 0:
      print "No lists to collapse."
      raw_input("Press Enter to continue...")
      return []
      
   collapsed = [ CELL_EMPTY for x in xrange(len(list_of_lists[0])) ]
   for i in xrange(len(list_of_lists[0])):
      value = list_of_lists[0][i]
      all_matched = True
      for list in list_of_lists:
         if list[i] != value:
            all_matched = False
            break
      
      # If every element in this column is identical, we know its value.
      if all_matched == True:
         # If each element is marked empty then it can't have an ID. Mark it as blank.
         #if value == CELL_EMPTY:
         #   value = CELL_BLANK
            
         collapsed[i] = value
   
   return collapsed   


# This function sums the currently used width based on an array of hints (tuples) and expansions.
# Typically will be used to check if we've exceeded the puzzle width.
def find_used_width(hints, expansions):
   used_width = 0
   
   # Sum hints. This should never change for this row.
   for h in hints:
      used_width += h[1]
      
   # Sum expansions. This will change with each recursive call.
   used_width += sum(expansions)
   
   return used_width


# This function checks if the grid is completed
def is_grid_complete(grid, left_hints, top_hints):
   # Check rows
   for row_idx in xrange(len(puzz_grid)):
      row = puzz_grid[row_idx]
      if not is_row_complete(row, left_hints[row_idx]):
         return False
      
   # Check columns
   for col_idx in xrange(len(puzz_grid[0])):
      col = [row[col_idx] for row in puzz_grid]
      if not is_row_complete(col, top_hints[col_idx]):
         return False
         
   # If we made it this far, the grid must be complete!
   return True


# This function determines if a row is completed. This logic can be applied to
# a column as well, the user just needs to transpose the column data to a row.
def is_row_complete(row, hints):
   if len(hints) == 0:
      return True
      
   # print "Checking:"
   # print "   row: " + str(row)
      
   col_idx = 0
   for hint in hints:
      id = hint[0]
      count = hint[1]
      
      # print ""
      # print "   hint: " + str(hint)
      
      hint_matched = False
      while hint_matched == False:
         if col_idx >= len(row):
            # Ran over the end of the row without finding a match for the hint
            # print "   Ran over length main loop"
            return False
            
         if row[col_idx] == id:
            # Found a cell that matches this hint, now make sure it matches the full hint
            # print "   Found beginning of hint " + str(hint)
            count = count - 1
            col_idx = col_idx + 1
            while count > 0:
               # print "      count: " + str(count)
               # print "      col_idx: " + str(col_idx)
               
               if col_idx >= len(row):
                  # Ran over the end of the row without finding the whole hint
                  # print "   Ran over length hint loop"
                  return False
                  
               if row[col_idx] != id:
                  # The hint has the correct ID but isn't the full length
                  # print "      Hint not long enough"
                  return False
               else:
                  count = count - 1
                  col_idx = col_idx + 1
            
            # If we made it this far, the hint was completely matched
            # print "   Hint matched!"
            hint_matched = True
            
         elif row[col_idx] == CELL_EMPTY or row[col_idx] == CELL_BLANK:
            # It's OK if there's a blank or empty cell before this hint is matched
            # print "   Found blank or empty at col_idx=" + str(col_idx)
            col_idx = col_idx + 1
         else:
            # We found a different ID than the hint was expecting. This probably means the row is wrong.
            # print "   ID doesn't match!"
            return False
            
   # If we made it through the whole row and each match and didn't have any issues then it must match!
   # print "Row is valid!"
   return True


# --- MAIN CODE BEGINS HERE ---
print ""

# System argument gives the puzzle ID, if not revert to a default
puzzle_id = 139714
if len(sys.argv) > 1:
   puzzle_id = int(sys.argv[1])

# Pull in the puzzle's solver page. This is the one that has the puzzle definition.
# If already exists on disk, just use that one. Otherwise grab from website and save to disk.
disk_file_name = "griddler{0}.txt".format(puzzle_id)
web_html = ""
if os.path.isfile(disk_file_name):
   print "Reading HTML from disk."
   f = open(disk_file_name, "r")
   web_html = f.read()
   f.close()
else:
   print "Reading HTML from website."
   web_url_base = 'http://www.griddlers.net/griddlers?p_p_id=griddlers_WAR_puzzles&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=html&p_p_cacheability=cacheLevelPage&p_p_col_id=column-2&p_p_col_count=1&_griddlers_WAR_puzzles_id={0}&_griddlers_WAR_puzzles_view=detail'
   web_url = web_url_base.format(puzzle_id) # Add the puzzle ID into the url
   web_file = urllib2.urlopen(web_url)
   web_html = web_file.read()
   
   print "Writing HTML to disk."
   f = open(disk_file_name, "w")
   f.write(web_html)
   f.close()
print "Page data retrieved."


# Extract puzzle details

# Puzzle width
result = re.search('var pwidth = ([0-9]+)', web_html)
puzz_width = int(result.group(1))
print "Puzzle width: " + str(puzz_width)

# Puzzle height
result = re.search('var pheight = ([0-9]+)', web_html)
puzz_height = int(result.group(1))
print "Puzzle height: " + str(puzz_height)

# Puzzle horizontal (left) codes
puzz_left_hints = []
for result in re.finditer('leftCodes\[[0-9]+\]=\"(.*)\";', web_html):
   left_hint_list = []
   for r in result.group(1).split(','):
      left_hint = re.search('([0-9]+):([0-9]+)', r)
      if left_hint:
         palette_id = int(left_hint.group(1))
         count = int(left_hint.group(2))
         left_hint_list.append( (palette_id, count) )
   puzz_left_hints.append(left_hint_list)

# Puzzle vertical (top) codes
puzz_top_hints = []
for result in re.finditer('topCodes\[[0-9]+\]=\"(.*)\";', web_html):
   top_hint_list = []
   for r in result.group(1).split(','):
      top_hint = re.search('([0-9]+):([0-9]+)', r)
      if top_hint:
         palette_id = int(top_hint.group(1))
         count = int(top_hint.group(2))
         top_hint_list.append( (palette_id, count) )
   puzz_top_hints.append(top_hint_list)


# Create puzzle grid
puzz_grid = [[CELL_EMPTY for x in xrange(puzz_width)] for x in xrange(puzz_height)]

# Search possibilities
while True:
   for row_idx in xrange(len(puzz_grid)):
      print "Row " + str(row_idx)
      
      row = puzz_grid[row_idx]
      hints = puzz_left_hints[row_idx]
      
      # Check if row is already valid before searching possibilities
      if is_row_complete(row, hints):
         # Row is complete, now replace any empty cells with blank.
         for col_idx in xrange(len(row)): # There may be a more efficient / pythonic way of doing this
            if row[col_idx] == CELL_EMPTY:
               row[col_idx] = CELL_BLANK
         # Store row of data back into the puzzle grid (copy of row is used, old row will be
         # garbage collected or something).
         puzz_grid[row_idx] = row
         print "   already complete!"
         #raw_input("Press Enter to continue...")
         continue
      
      success_list = search_possibilities(hints, row, puzz_width)
      # print "Successes:"
      # for x in success_list:
         # print x

      row = collapse_possibilities(success_list)
      print ""
      print "Collapsed: "
      print row
      
      # Check again if the row is valid, since we may have just completed it.
      # We do this now to pre-emptively fill in any empty cells with blank ones.
      if is_row_complete(row, hints):
         # Row is complete, now replace any empty cells with blank.
         for col_idx in xrange(len(row)): # There may be a more efficient / pythonic way of doing this
            if row[col_idx] == CELL_EMPTY:
               row[col_idx] = CELL_BLANK
         print "   just completed!"
      
      # Store row of data back into the puzzle grid (copy of row is used, old row will be
      # garbage collected or something).
      puzz_grid[row_idx] = row
      #raw_input("Press Enter to continue...")
      
   for col_idx in xrange(len(puzz_grid[0])):
      print "Col " + str(col_idx)
      
      col = [row[col_idx] for row in puzz_grid]
      hints = puzz_top_hints[col_idx]
      
      # Check if row is already valid before searching possibilities
      if is_row_complete(col, hints):
         # Column is complete, now replace any empty cells with blank.
         for row_idx in xrange(len(col)): # There may be a more efficient / pythonic way of doing this
            if col[row_idx] == CELL_EMPTY: # Make this an accessor function
               col[row_idx] = CELL_BLANK
         print "   already complete!"
         # Store column of data back into the puzzle grid.
         for i, row in enumerate(puzz_grid): # Make this an accessor function
            row[col_idx] = col[i]
         #raw_input("Press Enter to continue...")
         continue
      
      success_list = search_possibilities(hints, col, puzz_height)
      #print "Successes:"
      #for x in success_list:
      #   print x

      col = collapse_possibilities(success_list)
      print ""
      print "Collapsed: "
      print col
      
      # Check again if the column is valid, since we may have just completed it.
      # We do this now to pre-emptively fill in any empty cells with blank ones.
      if is_row_complete(col, hints):
         # Column is complete, now replace any empty cells with blank.
         for row_idx in xrange(len(col)): # There may be a more efficient / pythonic way of doing this
            if col[row_idx] == CELL_EMPTY:
               col[row_idx] = CELL_BLANK
         print "   just completed!"
      
      # Store column of data back into the puzzle grid.
      for i, row in enumerate(puzz_grid):
         row[col_idx] = col[i]
      #raw_input("Press Enter to continue...")
      
   print ""
   for row in puzz_grid:
      print row
      
   # Check if whole grid is valid now
   if is_grid_complete(puzz_grid, puzz_left_hints, puzz_top_hints):
      print "Grid is complete!!"
      break
      
   print "Grid not complete yet, iterating again..."
   #raw_input("Press Enter to continue...")

# Puzzle is complete!

# Could have a speedup where if the row is empty and the sum of the components isn't long enough,
# just skip the row and return all empties.
# Could collapse each new possibility with the last -- would be quicker and use less memory!
# Add NOT SOLVED detection
# I should really create a custom exception so that regular ones aren't getting caught in the search loop